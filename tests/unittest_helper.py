import os
import unittest

from ghost_client import Ghost, GhostException


class GhostTestCase(unittest.TestCase):
    GHOST_BASE_URL = os.environ.get('GHOST_BASE_URL', 'http://localhost:12368')
    GHOST_VERSION = os.environ.get('GHOST_VERSION', 'auto')
    GHOST_USERNAME = os.environ.get('GHOST_USERNAME', 'test@test.local')
    GHOST_PASSWORD = os.environ.get('GHOST_PASSWORD', 'abcd123456')

    def setUp(self):
        self.ghost = self._setup_client()

        self._posts_to_delete = list()
        self._tags_to_delete = list()
        self._users_to_delete = list()

    def tearDown(self):
        for post_id in self._posts_to_delete:
            self.ghost.posts.delete(post_id)

        for tag_id in self._tags_to_delete:
            self.ghost.tags.delete(tag_id)

        for user_id in self._users_to_delete:
            self.ghost.users.delete(user_id)

        self.ghost.logout()

    def _setup_client(self):
        raise NotImplementedError(
            'No "client" was set up (use "new_client" or "new_logged_in_client")'
        )

    def new_client(self, version=GHOST_VERSION):
        self._clear_rate_limit()

        return Ghost.from_sqlite(
            self._find_database(), self.GHOST_BASE_URL, version=version
        )

    def new_logged_in_client(self, version=GHOST_VERSION):
        client = self.new_client(version=version)
        self.login(client)
        return client

    def login(self, client=None, username=None, password=None):
        if client is None:
            client = self.ghost

        if username is None:
            username = self.GHOST_USERNAME

        if password is None:
            password = self.GHOST_PASSWORD

        return client.login(username, password)

    def enable_public_api(self, client=None):
        if client is None:
            client = self.ghost

        return client.execute_put('settings/', json={
            "settings": [{"key": "labs", "value": "{\"publicAPI\":true}"}]
        })

    @staticmethod
    def _clear_rate_limit():
        import os
        import sqlite3

        fd = os.open(GhostTestCase._find_database(), os.O_RDWR)
        connection = sqlite3.connect('/dev/fd/%d' % fd)
        os.close(fd)

        try:
            connection.executescript('delete from brute')
        except sqlite3.OperationalError:
            pass  # failed to delete the table, maybe can't write
        finally:
            connection.close()

    @staticmethod
    def _find_database():
        for filename in os.listdir(os.path.join(os.path.dirname(__file__), 'ghost-db')):
            if os.path.splitext(filename)[1] == '.db':
                return os.path.join(os.path.dirname(__file__), 'ghost-db/%s' % filename)

    def create_post(self, client=None, **kwargs):
        if client is None:
            client = self.ghost

        post = client.posts.create(**kwargs)
        self._posts_to_delete.append(post.id)
        return post

    def create_tag(self, client=None, **kwargs):
        if client is None:
            client = self.ghost

        tag = client.tags.create(**kwargs)
        self._tags_to_delete.append(tag.id)
        return tag

    def create_user(self, client=None, **kwargs):
        if client is None:
            client = self.ghost

        user = client.users.create(**kwargs)
        self._users_to_delete.append(user.id)
        return user
