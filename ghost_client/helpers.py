import functools


def refresh_session_if_necessary(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            result = f(self, *args, **kwargs)
        except Exception as ex:
            if hasattr(ex, 'code') and ex.code == 401:
                self.refresh_session()
                # retry now
                result = f(self, *args, **kwargs)
            else:
                raise ex

        return result

    return wrapped
