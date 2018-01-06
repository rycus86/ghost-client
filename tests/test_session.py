try:
    from .unittest_helper import GhostTestCase, Ghost, GhostException
except:
    from unittest_helper import GhostTestCase, Ghost, GhostException


class SessionTest(GhostTestCase):
    def _setup_client(self):
        return self.new_client()

    def test_login(self):
        self.assertNotEqual(len(self.login()), 0)

    def test_invalid_login(self):
        self.assertRaises(GhostException, self.login, username='fake', password='fake')

    def test_no_client_id_or_secret(self):
        self.assertRaises(GhostException, Ghost, self.GHOST_BASE_URL, client_id=None, client_secret=None)
        self.assertRaises(GhostException, Ghost, self.GHOST_BASE_URL, client_id='x', client_secret=None)
        self.assertRaises(GhostException, Ghost, self.GHOST_BASE_URL, client_id=None, client_secret='y')

    def test_invalid_client_id(self):
        self.assertRaises(
            GhostException, Ghost.from_sqlite, self._find_database(), self.GHOST_BASE_URL, client_id='fake'
        )

    def test_change_without_login(self):
        logged_in = self.new_logged_in_client()

        post = None

        try:
            post = self.create_post(logged_in, title='Existing')

            self.assertRaises(GhostException, self.ghost.posts.create, title='Failing')
            self.assertRaises(GhostException, self.ghost.posts.update, id=post.id, title='Failing')
            self.assertRaises(GhostException, self.ghost.posts.delete, id=post.id)

        finally:
            logged_in.posts.delete(post.id)
            self._posts_to_delete.remove(post.id)
            logged_in.logout()

    def test_logout(self):
        client = self.new_logged_in_client()

        self.assertGreater(len(client.posts.list(status='all')), 0)

        client.logout()

        self.assertRaises(GhostException, client.posts.list, status='all')

    def test_refresh_token(self):
        client = self.new_logged_in_client()

        self.assertGreater(len(client.posts.list(status='all')), 0)

        client.revoke_access_token()

        self.assertGreater(len(client.posts.list(status='all')), 0)

    def test_reauthenticate(self):
        client = self.new_logged_in_client()

        self.assertGreater(len(client.posts.list(status='all')), 0)

        client.revoke_refresh_token()
        client.revoke_access_token()

        self.assertGreater(len(client.posts.list(status='all')), 0)

    def test_version(self):
        client = self.new_client(version='auto')

        try:
            self.assertEqual('1', client.version)

            self.login(client)

            self.assertNotEqual('1', client.version)

        finally:
            client.logout()

    def test_version_caching(self):
        client = self.new_client(version='auto')

        try:
            counters = dict()

            _exec_get = client.execute_get

            def counting_get(resource, *args, **kwargs):
                if resource not in counters:
                    counters[resource] = 1
                else:
                    counters[resource] += 1

                return _exec_get(resource, *args, **kwargs)

            client.execute_get = counting_get

            for _ in range(3):
                self.assertEqual('1', client.version)

            self.assertEqual(counters['configuration/about/'], 3)

            counters.clear()

            self.login(client)

            for _ in range(3):
                self.assertNotEqual('1', client.version)

            self.assertEqual(counters['configuration/about/'], 1)

        finally:
            client.logout()
