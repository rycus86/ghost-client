class GhostException(Exception):
    """
    Type of exceptions raised by the client.
    """

    def __init__(self, code, errors):
        """
        Constructor.

        :param code: The HTTP status code returned by the API
        :param errors: The `errors` field returned in the response JSON
        """

        super(GhostException, self).__init__(code, errors)
        self.code = code
        self.errors = errors


class GhostRequestException(GhostException):
    """
    Extended exception type that includes the URI where the error happened.
    """

    def __init__(self, code, path, errors):
        """
        Constructor.

        :param code: The HTTP status code returned by the API
        :param path: The URI where the error happened
        :param errors: The `errors` field returned in the response JSON
        """

        super(GhostException, self).__init__(code, path, errors)
        self.code = code
        self.path = path
        self.errors = errors
