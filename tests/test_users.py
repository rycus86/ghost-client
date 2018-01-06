try:
    from .unittest_helper import GhostTestCase, GhostException
except:
    from unittest_helper import GhostTestCase, GhostException


class UserTests(GhostTestCase):
    def _setup_client(self):
        return self.new_logged_in_client()

    def test_create_post_with_user(self):
        user = next(iter(self.ghost.users.list()))

        post = self.create_post(title='Post with author', author_id=user.id)

        stored = self.ghost.posts.get(post.id, include='author', status='all')

        self.assertEqual(stored.id, post.id)
        self.assertEqual(stored.title, 'Post with author')
        self.assertIsNotNone(stored.author)
        self.assertEqual(stored.author.name, user.name)

    def test_list_without_login(self):
        all_users = self.ghost.users.list()

        self.enable_public_api()

        users = self.new_client().users.list(fields='name')

        for user in all_users:
            self.assertIn({'name': user.name}, users)

    def test_get_user(self):
        user = next(iter(self.ghost.users.list()))

        by_id = self.ghost.users.get(user.id)
        self.assertEqual(by_id.id, user.id)

        by_id = self.ghost.users.get(id=user.id)
        self.assertEqual(by_id.id, user.id)

        by_slug = self.ghost.users.get(slug=user.slug)
        self.assertEqual(by_slug.id, user.id)

    def test_pagination(self):
        all_users = self.ghost.users.list()
        users = self.ghost.users.list(limit=1)

        self.assertEqual(users.total, len(all_users))
        self.assertEqual(users.pages, len(all_users))
        self.assertEqual(users.limit, 1)
        self.assertIsNone(users.prev_page())

        last = None

        for _ in range(users.pages):
            last, users = users, users.next_page()

            if not users:
                break

            self.assertIsNotNone(users.prev_page())

        self.assertIsNone(last.next_page())

    def test_invalid_user(self):
        self.assertRaises(GhostException, self.ghost.users.create, created_at='xyz', name='Invalid User')
