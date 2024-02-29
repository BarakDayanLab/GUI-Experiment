import functools
from threading import Timer


class SetInterval(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def use_lock(lock_str="lock"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_str)
            lock.acquire()
            result = func(self, *args, **kwargs)
            lock.release()
            return result
        return wrapper
    return decorator
