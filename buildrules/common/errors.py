import sys
import logging
import traceback
from io import StringIO

def log_error_and_quit(function):
    """log_error_and_quit is a decorator that logs errors, prints
    stack trace and then quits.

    Args:
        function (function): Function that will be decorated.

    Returns:
        exception_wrapper: Decorated function.
    """

    def exception_wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            logging.error('Encountered an error:\n\n%s', error)
            trace = StringIO()
            traceback.print_stack(file=trace)
            logging.error(trace.getvalue())
            trace.close()
            sys.exit(1)
    return exception_wrapper
