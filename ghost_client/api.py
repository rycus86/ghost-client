import os
import mimetypes

import six
import requests

from .models import Controller, PostController
from .helpers import refresh_session_if_necessary
from .errors import GhostException, GhostRequestException


class Ghost(object):
    """
    API client for the Ghost REST endpoints.
    See https://api.ghost.org/ for the available parameters.

    Sample usage:

        from ghost_client import Ghost

        # to read the client ID and secret from the database
        ghost = Ghost.from_sqlite(
            '/var/lib/ghost/content/data/ghost.db',
            'http://localhost:2368'
        )

        # or to use a specific client ID and secret
        ghost = Ghost(
            'http://localhost:2368',
            client_id='ghost-admin', client_secret='secret_key'
        )

        # log in
        ghost.login('username', 'password')

        # print the server's version
        print(ghost.version)

        # create a new tag
        tag = ghost.tags.create(name='API sample')

        # create a new post using it
        post = ghost.posts.create(
            title='Example post', slug='custom-slug',
            markdown='',  # yes, even on v1.+
            custom_excerpt='An example post created from Python',
            tags=[tag]
        )

        # list posts, tags and users
        posts = ghost.posts.list(
            status='all',
            fields=('id', 'title', 'slug'),
            formats=('html', 'mobiledoc', 'plaintext'),
        )
        tags = ghost.tags.list(fields='name', limit='all')
        users = ghost.users.list(include='count.posts')

        # use pagination
        while posts:
            for post in posts:
                print(post)
                posts = posts.next_page()

        print(posts.total)
        print(posts.pages)

        # update a post & tag
        updated_post = ghost.posts.update(post.id, title='Updated title')
        updated_tag = ghost.tags.update(tag.id, name='Updated tag')

        # note: creating, updating and deleting a user is not allowed by the API

        # access fields as properties
        print(post.title)
        print(post.markdown)     # needs formats='mobiledoc'
        print(post.author.name)  # needs include='author'

        # delete a post & tag
        ghost.posts.delete(post.id)
        ghost.tags.delete(tag.id)

        # upload an image
        ghost.upload(file_obj=open('sample.png', 'rb'))
        ghost.upload(file_path='/path/to/image.jpeg', 'rb')
        ghost.upload(name='image.gif', data=open('local.gif', 'rb').read())

        # log out
        ghost.logout()

    The logged in credentials will be saved in memory and
    on HTTP 401 errors the client will attempt
    to re-authenticate once automatically.

    Responses are wrapped in `models.ModelList` and `models.Model`
    types to allow pagination and retrieving fields as properties.
    """

    DEFAULT_VERSION = '1'
    """
    The default version to report when cannot be fetched.
    """

    def __init__(
            self, base_url, version='auto', **kwargs
    ):
        """
        Creates a new Ghost API client.

        :param base_url: The base url of the server
        :param version: The server version to use (default: `auto`)
        :param client_id: Self-supplied client ID (optional)
        :param client_secret: Self-supplied client secret (optional)
        :param access_token: Self-supplied access token (optional)
        :param refresh_token: Self-supplied refresh token (optional)
        """

        self.base_url = '%s/ghost/api' % base_url
        self._api_version = 'auto'
        self._version = version

        self._session_cookie = kwargs.get('session_cookie')

        # deprecated
        self._client_id = kwargs.get('client_id')
        self._client_secret = kwargs.get('client_secret')
        self._access_token = kwargs.get('access_token')
        self._refresh_token = kwargs.get('refresh_token')

        self._username = None
        self._password = None

        if not self._client_id or not self._client_secret:  # TODO
            raise GhostException(401, [{
                'errorType': 'InternalError',
                'message': 'No client_id or client_secret given or found'
            }])

        self.posts = PostController(self)
        self.tags = Controller(self, 'tags')
        self.users = Controller(self, 'users')

    @classmethod
    def from_sqlite(cls, database_path, base_url, version='auto', client_id='ghost-admin'):
        """
        Initialize a new Ghost API client,
        reading the client ID and secret from the SQlite database.

        :param database_path: The path to the database file.
        :param base_url: The base url of the server
        :param version: The server version to use (default: `auto`)
        :param client_id: The client ID to look for in the database
        :return: A new Ghost API client instance
        """

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
                return cls(
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
        """
        :return: The version of the server when initialized as 'auto',
            otherwise the version passed in at initialization
        """

        if self._version != 'auto':
            return self._version

        if self._version == 'auto':
            # Try the old API
            try:
                data = self.execute_get('configuration/about/', api_version='v0.1', anonymous=True)
                self._version = data['configuration'][0]['version']
            except GhostException:
                # Try the new API
                try:
                    data = self.execute_get('site/', api_version='v2/admin', anonymous=True)
                    self._version = data['site']['version']
                except GhostException:
                    return self.DEFAULT_VERSION

        return self._version

    @property
    def api_version(self):  # TODO docs
        if self._api_version == 'auto':
            self._api_version = 'v0.1' if self.version < '2' else 'v2/admin'

        return self._api_version

    def login(self, username, password):
        """
        Authenticate with the server.

        :param username: The username of an existing user
        :param password: The password for the user
        :return: The authentication response from the REST endpoint
        """

        # TODO API key

        if self.version < '2':
            data = self._deprecated_authenticate(
                grant_type='password',
                username=username,
                password=password,
                client_id=self._client_id,
                client_secret=self._client_secret
            )

        else:
            data = self._authenticate(
                username=username,
                password=password
            )

        self._username = username
        self._password = password

        return data

    def refresh_session(self):
        """
        Re-authenticate using the refresh token if available.
        Otherwise log in using the username and password
        if it was used to authenticate initially.

        :return: The authentication response or `None` if not available
        """

        if not self._refresh_token:
            if self._username and self._password:
                return self.login(self._username, self._password)

            return

        return self._deprecated_authenticate(
            grant_type='refresh_token',
            refresh_token=self._refresh_token,
            client_id=self._client_id,
            client_secret=self._client_secret
        )

    def _authenticate(self, **kwargs):
        response = requests.post(
            '%s/%s/session' % (self.base_url, self.api_version), data=kwargs, headers={'Origin': self.base_url}
        )

        if response.status_code != 201:
            raise GhostRequestException(
                response.status_code,
                response.request.path_url,
                response.json().get('errors', [])
            )

        self._session_cookie = response.cookies.get('ghost-admin-api-session')

        return response.text

    def _deprecated_authenticate(self, **kwargs):
        response = requests.post(
            '%s/%s/authentication/token' % (self.base_url, self.api_version), data=kwargs
        )

        if response.status_code != 200:
            raise GhostRequestException(
                response.status_code,
                response.request.path_url,
                response.json().get('errors', [])
            )

        data = response.json()

        self._access_token = data.get('access_token')
        self._refresh_token = data.get('refresh_token')

        return data

    def revoke_access_token(self):
        """
        Revoke the access token currently in use.
        """

        if not self._access_token:
            return

        self.execute_post('authentication/revoke', json=dict(
            token_type_hint='access_token',
            token=self._access_token
        ))

        self._access_token = None

    def revoke_refresh_token(self):
        """
        Revoke the refresh token currently active.
        """

        if not self._refresh_token:
            return

        self.execute_post('authentication/revoke', json=dict(
            token_type_hint='refresh_token',
            token=self._refresh_token
        ))

        self._refresh_token = None

    def logout(self):
        """
        Log out, revoking the access tokens
        and forgetting the login details if they were given.
        """

        self.revoke_refresh_token()
        self.revoke_access_token()

        self._username, self._password, self._session_cookie = None, None, None

    def upload(self, file_obj=None, file_path=None, name=None, data=None):
        """
        Upload an image and return its path on the server.
        Either `file_obj` or `file_path` or `name` and `data` has to be specified.

        :param file_obj: A file object to upload
        :param file_path: A file path to upload from
        :param name: A file name for uploading
        :param data: The file content to upload
        :return: The path of the uploaded file on the server
        """

        close = False

        if file_obj:
            file_name, content = os.path.basename(file_obj.name), file_obj

        elif file_path:
            file_name, content = os.path.basename(file_path), open(file_path, 'rb')
            close = True

        elif name and data:
            file_name, content = name, data

        else:
            raise GhostException(
                400,
                'Either `file_obj` or `file_path` or '
                '`name` and `data` needs to be specified'
            )

        try:
            content_type, _ = mimetypes.guess_type(file_name)

            file_arg = (file_name, content, content_type)

            if self.version < '2':
                response = self.execute_post('uploads/', files={'uploadimage': file_arg})

            else:
                response = self.execute_post('images/upload/', files={'file': file_arg})

            return response

        finally:
            if close:
                content.close()

    @refresh_session_if_necessary
    def execute_get(self, resource, **kwargs):
        """
        Execute an HTTP GET request against the API endpoints.
        This method is meant for internal use.

        :param resource: The last part of the URI
        :param kwargs: Additional query parameters (and optionally headers)
        :return: The HTTP response as JSON or `GhostException` if unsuccessful
        """

        api_version = kwargs.pop('api_version', None)
        if not api_version:
            api_version = self.api_version

        url = '%s/%s/%s' % (self.base_url, api_version, resource)

        headers = kwargs.pop('headers', dict())

        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'
        headers['Origin'] = self.base_url

        if kwargs:
            separator = '&' if '?' in url else '?'

            for key, value in kwargs.items():
                if hasattr(value, '__iter__') and type(value) not in six.string_types:
                    url = '%s%s%s=%s' % (url, separator, key, ','.join(value))

                else:
                    url = '%s%s%s=%s' % (url, separator, key, value)

                separator = '&'

        if self._session_cookie:
            headers['Cookie'] = 'ghost-admin-api-session=%s' % self._session_cookie
        elif self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token

        elif self._version < '2':
            separator = '&' if '?' in url else '?'
            url = '%s%sclient_id=%s&client_secret=%s' % (
                url, separator, self._client_id, self._client_secret
            )

        response = requests.get(url, headers=headers)

        if response.status_code // 100 != 2:
            raise GhostRequestException(
                response.status_code,
                response.request.path_url,
                response.json().get('errors', [])
            )

        try:
            return response.json()
        except Exception:
            raise GhostException(400, [{
                'errorType': 'ClientError',
                'message': 'Failed to decode JSON response [content-type: %s]' % response.headers.get('Content-Type')
            }])

    def execute_post(self, resource, **kwargs):
        """
        Execute an HTTP POST request against the API endpoints.
        This method is meant for internal use.

        :param resource: The last part of the URI
        :param kwargs: Additional parameters for the HTTP call (`request` library)
        :return: The HTTP response as JSON or `GhostException` if unsuccessful
        """

        return self._request(resource, requests.post, **kwargs).json()

    def execute_put(self, resource, **kwargs):
        """
        Execute an HTTP PUT request against the API endpoints.
        This method is meant for internal use.

        :param resource: The last part of the URI
        :param kwargs: Additional parameters for the HTTP call (`request` library)
        :return: The HTTP response as JSON or `GhostException` if unsuccessful
        """

        return self._request(resource, requests.put, **kwargs).json()

    def execute_delete(self, resource, **kwargs):
        """
        Execute an HTTP DELETE request against the API endpoints.
        This method is meant for internal use.
        Does not return anything but raises an exception when failed.

        :param resource: The last part of the URI
        :param kwargs: Additional parameters for the HTTP call (`request` library)
        """

        self._request(resource, requests.delete, **kwargs)

    @refresh_session_if_necessary
    def _request(self, resource, request, **kwargs):
        url = '%s/%s/%s' % (self.base_url, self.api_version, resource)

        headers = kwargs.pop('headers', dict())
        headers['Origin'] = self.base_url

        if 'json' in kwargs:
            headers['Accept'] = 'application/json'
            headers['Content-Type'] = 'application/json'

        if self._session_cookie:
            headers['Cookie'] = 'ghost-admin-api-session=%s' % self._session_cookie
        elif self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token
        else:
            raise GhostException(401, [{
                'errorType': 'ClientError',
                'message': 'Access token not found'
            }])

        response = request(url, headers=headers, **kwargs)

        if response.status_code // 100 != 2:
            raise GhostRequestException(
                response.status_code,
                response.request.path_url,
                response.json().get('errors', [])
            )

        return response
