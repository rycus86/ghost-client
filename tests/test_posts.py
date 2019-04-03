import math

try:
    from .unittest_helper import GhostTestCase, GhostException
except:
    from unittest_helper import GhostTestCase, GhostException


class PostTests(GhostTestCase):
    def _setup_client(self):
        return self.new_logged_in_client()

    def test_create_post(self):
        post = self.create_post(title='Sample Post Title')

        self.assertIn({'id': post.id}, self.ghost.posts.list(fields='id', status='all'))

    def test_edit_post(self):
        post = self.create_post(title='Sample Post Update')

        updated = self.ghost.posts.update(post.id, slug='update-sample',
                                          updated_at=post.updated_at,
                                          markdown='Intro\n\n## Section\n\nBody content')

        self.assertEqual(updated.id, post.id)

        self.assertIn({'id': post.id}, self.ghost.posts.list(fields='id', status='all'))

        posts = self.ghost.posts.list(filter='id:%s' % post.id,
                                      status='all', formats='html')

        self.assertEqual(len(posts), 1)

        stored = posts[0]

        for text in ('Intro', 'Section', 'Body content'):
            self.assertIn(text, stored.html)

    def test_delete_post(self):
        post = self.ghost.posts.create(title='Sample Post to Delete')

        self.assertIn({'id': post.id}, self.ghost.posts.list(fields='id', status='all'))

        self.ghost.posts.delete(post.id)

        self.assertNotIn({'id': post.id}, self.ghost.posts.list(fields='id', status='all'))

    def test_publish(self):
        post = self.create_post(title='Sample to publish')

        posts = self.ghost.posts.list(fields='id')

        # self.assertNotIn({'id': post.id}, posts)  # TODO

        post.slug = 'publish-test'
        post.markdown = 'Content'

        updated = self.ghost.posts.update(**{k: v for k, v in post.items() if k not in ('comment_id', 'uuid')})

        self.ghost.posts.update(post.id, updated_at=updated.updated_at, status='published')

        posts = self.ghost.posts.list(
            filter='id:%s' % post.id,
            fields=('id', 'title', 'slug', 'html'),
            formats='html'
        )

        self.assertEqual(len(posts), 1)

        stored = posts[0]

        self.assertEqual(stored.id, post.id)
        self.assertEqual(stored.title, post.title)
        self.assertEqual(stored.slug, post.slug)
        self.assertIn('<p>Content</p>', stored.html)

    def test_get_post(self):
        post = self.create_post(title='For testing', status='published')

        by_id = self.ghost.posts.get(post.id)
        self.assertEqual(post.id, by_id.id)

        by_id = self.ghost.posts.get(id=post.id)
        self.assertEqual(post.id, by_id.id)

        by_slug = self.ghost.posts.get(slug=post.slug)
        self.assertEqual(post.id, by_slug.id)

    def test_markdown(self):
        self.create_post(title='Sample for Markdown', markdown='Line 1\n\n## Section 2\n\nBody 3')

        posts = self.ghost.posts.list(formats='mobiledoc', status='all')

        self.assertTrue(any(
            post.title == 'Sample for Markdown' and
            post.markdown == 'Line 1\n\n## Section 2\n\nBody 3'
            for post in posts
        ))

    def test_list_without_login(self):
        self.create_post(title='Test Post A', status='published')
        self.create_post(title='Test Post B', status='published')

        self.enable_public_api()

        posts = self.new_client().posts.list(fields='title')

        self.assertIn({'title': 'Test Post A'}, posts)
        self.assertIn({'title': 'Test Post B'}, posts)

    def test_pagination(self):
        preexisting = len(self.ghost.posts.list(status='draft'))

        for idx in range(10):
            self.create_post(title='Testing post #%d' % idx)

        posts = self.ghost.posts.list(status='draft', limit=3)

        self.assertEqual(posts.total, 10 + preexisting)
        self.assertEqual(posts.pages, math.ceil((10 + preexisting) / 3.0))
        self.assertEqual(posts.limit, 3)
        self.assertIsNone(posts.prev_page())

        last = None

        for _ in range(posts.pages):
            last, posts = posts, posts.next_page()

            if not posts:
                break

            self.assertIsNotNone(posts.prev_page())

        self.assertIsNone(last.next_page())

    def test_filter_by_authors(self):
        if self.ghost.version < '1.22.0':
            self.skipTest(
                'Multiple authors are not supported on version %s (< 1.22.0)' %
                self.ghost.version
            )

        users = self.ghost.users.list()

        self.assertGreater(len(users), 1)

        created = self.create_post(title='Multiple authors', authors=users)

        for user in users:
            posts = self.ghost.posts.list(
                filter='authors:[%s]' % user.slug, status='draft'
            )

            self.assertGreater(len(posts), 0)
            self.assertIn(created.id, list(p.id for p in posts))

    def test_invalid_post(self):
        self.assertRaises(GhostException, self.ghost.posts.create, uuid='xyz')

    def test_invalid_get(self):
        self.assertRaises(GhostException, self.ghost.posts.get, title='Without ID or Slug')
