import functools


def refresh_session_if_necessary(f):
    """
    Decorator to use on methods that are allowed
    to retry the request after reauthenticating the client.

    :param f: The original function
    :return: The decorated function
    """

    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            result = f(self, *args, **kwargs)
        except Exception as ex:
            if hasattr(ex, 'code') and ex.code in (401, 403):
                self.refresh_session()
                # retry now
                result = f(self, *args, **kwargs)
            else:
                raise ex

        return result

    return wrapped
