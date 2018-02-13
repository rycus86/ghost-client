import os

try:
    from .unittest_helper import GhostTestCase, GhostException
except:
    from unittest_helper import GhostTestCase, GhostException


class UploadTests(GhostTestCase):
    def __init__(self, *args, **kwargs):
        super(UploadTests, self).__init__(*args, **kwargs)

        if not hasattr(self, 'assertRegex'):
            self.assertRegex = self.assertRegexpMatches

    def _setup_client(self):
        return self.new_logged_in_client()

    def test_upload_from_file_obj(self):
        file_path = os.path.join(os.path.dirname(__file__), 'images/ghost-icon-1.png')

        with open(file_path, 'rb') as image_file:
            response = self.ghost.upload(file_obj=image_file)

        self.assertRegex(response, '/content/images/[0-9]{4}/[0-9]{2}/ghost-icon-1.png')

    def test_upload_from_file_path(self):
        file_path = os.path.join(os.path.dirname(__file__), 'images/ghost-icon-2.png')

        response = self.ghost.upload(file_path=file_path)

        self.assertRegex(response, '/content/images/[0-9]{4}/[0-9]{2}/ghost-icon-2.png')

    def test_upload_from_data(self):
        file_path = os.path.join(os.path.dirname(__file__), 'images/ghost-icon-1.png')

        with open(file_path, 'rb') as image_file:
            data = image_file.read()

        response = self.ghost.upload(name='custom-name.png', data=data)

        self.assertRegex(response, '/content/images/[0-9]{4}/[0-9]{2}/custom-name.png')

    def test_invalid_arguments(self):
        self.assertRaises(GhostException, self.ghost.upload)
