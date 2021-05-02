import logging
from functools import wraps
from time import perf_counter


logger = logging.getLogger(__name__)


def timeit(func):
    """A simple decorator to time execution of functions"""

    @wraps(func)
    def inner(*args, **kwargs):
        t1 = perf_counter()
        returnvalue = func(*args, **kwargs)
        logger.debug(f"{func.__name__} spent {perf_counter() - t1} seconds")
        return returnvalue

    return inner
