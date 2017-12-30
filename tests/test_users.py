try:
    from .unittest_helper import GhostTestCase, GhostException
except:
    from unittest_helper import GhostTestCase, GhostException


class UserTests(GhostTestCase):
    def _setup_client(self):
        return self.new_logged_in_client()

    # TODO
