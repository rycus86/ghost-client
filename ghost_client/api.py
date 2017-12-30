import six
import requests

from .models import Controller, PostController
from .helpers import refresh_session_if_necessary


class Ghost(object):
    DEFAULT_VERSION = '1'

    def __init__(
            self, base_url, version='auto',
            client_id=None, client_secret=None,
            access_token=None, refresh_token=None
    ):
        self.base_url = '%s/ghost/api/v0.1' % base_url
        self._version = version

        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = access_token
        self._refresh_token = refresh_token

        self._username = None
        self._password = None

        if not self._client_id or not self._client_secret:
            raise GhostException(401, [{
                'errorType': 'InternalError',
                'message': 'No client_id or client_secret given or found'
            }])

        self.posts = PostController(self)
        self.tags = Controller(self, 'tags')
        self.users = Controller(self, 'users')

    @classmethod
    def from_sqlite(cls, database_path, base_url, version='auto', client_id='ghost-admin'):
        import os
        import sqlite3

        fd = os.open(database_path, os.O_RDONLY)
        connection = sqlite3.connect('/dev/fd/%d' % fd)
        os.close(fd)

        try:
            row = connection.execute(
                'SELECT secret FROM clients WHERE slug = ?',
                (client_id,)
            ).fetchone()

            if row:
                return Ghost(
                    base_url, version=version,
                    client_id=client_id, client_secret=row[0]
                )

            else:
                raise GhostException(401, [{
                    'errorType': 'InternalError',
                    'message': 'No client_secret found for client_id: %s' % client_id
                }])

        finally:
            connection.close()

    @property
    def version(self):
        if self._version != 'auto':
            return self._version

        if self._version == 'auto':
            try:
                data = self.execute_get('configuration/about/')
                self._version = data['configuration'][0]['version']
            except GhostException:
                return self.DEFAULT_VERSION

        return self._version

    def login(self, username, password):
        data = self._authenticate(
            grant_type='password',
            username=username,
            password=password,
            client_id=self._client_id,
            client_secret=self._client_secret
        )

        self._username = username
        self._password = password

        return data

    def refresh_session(self):
        if not self._refresh_token:
            return

        return self._authenticate(
            grant_type='refresh_token',
            refresh_token=self._refresh_token,
            client_id=self._client_id,
            client_secret=self._client_secret
        )

    def _authenticate(self, **kwargs):
        response = requests.post(
            '%s/authentication/token' % self.base_url, data=kwargs
        )

        if response.status_code != 200:
            raise GhostException(response.status_code, response.json().get('errors', []))

        data = response.json()

        self._access_token = data.get('access_token')
        self._refresh_token = data.get('refresh_token')

        return data

    def revoke_access_token(self):
        if not self._access_token:
            return

        self.execute_post('authentication/revoke', json=dict(
            token_type_hint='access_token',
            token=self._access_token
        ))

    def revoke_refresh_token(self):
        if not self._refresh_token:
            return

        self.execute_post('authentication/revoke', json=dict(
            token_type_hint='refresh_token',
            token=self._refresh_token
        ))

    def logout(self):
        self.revoke_refresh_token()
        self.revoke_access_token()

    @refresh_session_if_necessary
    def execute_get(self, resource, **kwargs):
        url = '%s/%s' % (self.base_url, resource)

        headers = kwargs.pop('headers', dict())

        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'

        if kwargs:
            separator = '&' if '?' in url else '?'

            for key, value in kwargs.items():
                if hasattr(value, '__iter__') and type(value) not in six.string_types:
                    url = '%s%s%s=%s' % (url, separator, key, ','.join(value))

                else:
                    url = '%s%s%s=%s' % (url, separator, key, value)

                separator = '&'

        if self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token

        else:
            separator = '&' if '?' in url else '?'
            url = '%s%sclient_id=%s&client_secret=%s' % (
                url, separator, self._client_id, self._client_secret
            )

        response = requests.get(url, headers=headers)

        if response.status_code // 100 != 2:
            raise GhostException(response.status_code, response.json().get('errors', []))

        return response.json()

    def execute_post(self, resource, **kwargs):
        return self._request(resource, requests.post, **kwargs).json()

    def execute_put(self, resource, **kwargs):
        return self._request(resource, requests.put, **kwargs).json()

    def execute_delete(self, resource, **kwargs):
        self._request(resource, requests.delete, **kwargs)

    @refresh_session_if_necessary
    def _request(self, resource, request, **kwargs):
        if not self._access_token:
            raise GhostException(401, [{
                'errorType': 'ClientError',
                'message': 'Access token not found'
            }])

        url = '%s/%s' % (self.base_url, resource)

        headers = kwargs.pop('headers', dict())

        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'

        if self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token

        response = request(url, headers=headers, **kwargs)

        if response.status_code // 100 != 2:
            raise GhostException(response.status_code, response.json().get('errors', []))

        return response


class GhostException(Exception):
    def __init__(self, code, errors):
        super(GhostException, self).__init__(code, errors)
        self.code = code
        self.errors = errors
