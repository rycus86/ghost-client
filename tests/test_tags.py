import math

try:
    from .unittest_helper import GhostTestCase, GhostException
except:
    from unittest_helper import GhostTestCase, GhostException


class TagTests(GhostTestCase):
    def _setup_client(self):
        return self.new_logged_in_client()

    def test_create_tag(self):
        tag = self.create_tag(name='Example tag')

        self.assertIn({'id': tag.id}, self.ghost.tags.list(fields='id'))

    def test_edit_tag(self):
        tag = self.create_tag(name='Tag to edit')

        updated = self.ghost.tags.update(tag.id, name='Tag after update',
                                         slug='updated-tag', visibility='internal')

        self.assertEqual(updated.id, tag.id)

        self.assertIn({'id': tag.id}, self.ghost.tags.list(fields='id'))

        tags = self.ghost.tags.list(filter='id:%s' % tag.id)

        self.assertEqual(len(tags), 1)

        stored = tags[0]

        self.assertEqual(stored.name, 'Tag after update')
        self.assertEqual(stored.slug, 'updated-tag')
        self.assertEqual(stored.visibility, 'internal')

    def test_delete_tag(self):
        tag = self.ghost.tags.create(name='Tag to delete')

        self.assertIn({'id': tag.id}, self.ghost.tags.list(fields='id'))

        self.ghost.tags.delete(tag.id)

        self.assertNotIn({'id': tag.id}, self.ghost.tags.list(fields='id'))

    def test_create_post_with_tag(self):
        tag = self.create_tag(name='Tag for post')

        post = self.create_post(title='Tagged post', tags=[tag])

        stored = self.ghost.posts.get(post.id, include='tags', status='all')

        self.assertEqual(stored.id, post.id)
        self.assertEqual(stored.title, 'Tagged post')
        self.assertEqual(len(stored.tags), 1)
        self.assertEqual(stored.tags[0].name, 'Tag for post')

    def test_list_without_login(self):
        self.create_tag(name='Test Tag A')
        self.create_tag(name='Test Tag B')

        self.enable_public_api()

        tags = self.new_client().tags.list(fields='name')

        self.assertIn({'name': 'Test Tag A'}, tags)
        self.assertIn({'name': 'Test Tag B'}, tags)

    def test_get_tag(self):
        tag = self.create_tag(name='For testing', slug='test-tag')

        by_id = self.ghost.tags.get(tag.id)
        self.assertEqual(by_id.id, tag.id)

        by_id = self.ghost.tags.get(id=tag.id)
        self.assertEqual(by_id.id, tag.id)

        by_slug = self.ghost.tags.get(slug=tag.slug)
        self.assertEqual(by_slug.id, tag.id)

    def test_pagination(self):
        preexisting = len(self.ghost.tags.list())

        for idx in range(10):
            self.create_tag(name='Testing tag #%d' % idx)

        tags = self.ghost.tags.list(limit=3)

        self.assertEqual(tags.total, 10 + preexisting)
        self.assertEqual(tags.pages, math.ceil((10 + preexisting) / 3.0))
        self.assertEqual(tags.limit, 3)
        self.assertIsNone(tags.prev_page())

        last = None

        for _ in range(tags.pages):
            last, tags = tags, tags.next_page()

            if not tags:
                break

            self.assertIsNotNone(tags.prev_page())

        self.assertIsNone(last.next_page())

    def test_invalid_tag(self):
        self.assertRaises(GhostException, self.ghost.tags.create, uuid='xyz', name='Invalid Tag')
