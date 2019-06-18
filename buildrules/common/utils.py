# -*- coding: utf-8 -*-
"""Utilities module for buildrules.

This module contains utilities used by various buildrules.
"""

import logging
import sys

from functools import wraps

from contextlib import contextmanager

from io import StringIO

class StreamLogger:
    """This class acts as a stream and will write messages sent to the
    stream using logwriter.

    Args:
        logwriter (function): Logging function used to write the stream.

    Attributes:
        _msg (str): Message that will be written by logwriter.
        _writer (function): Stored logwriter.
    """

    def __init__(self, logwriter):
        self._writer = logwriter
        self._msg = ''

    def write(self, message):
        """Writes message using logwriter.

        Args:
            message (str): Message that needs to be written.
        """
        self._msg = self._msg + message
        while '\n' in self._msg:
            pos = self._msg.find('\n')
            self._writer(self._msg[:pos])
            self._msg = self._msg[pos+1:]

    def flush(self):
        """Flush _msg to _writer."""
        if self._msg != '':
            self._writer(self._msg)
            self._msg = ''

def stdstreams_to_logger(stdout_writer=logging.info, stderr_writer=logging.warning):
    """This function parametrizes the decorator logger_decorator, that
    diverts stdout and stderr to logging streams.

    Args:
        stdout_writer (function, optional): Function that will be used for writing
            the stdout stream. Defaults to `logging.info`.
        stderr_writer (function, optional): Function that will be used for writing
            the stderr stream. Defaults to `logging.warning`.

    Returns:
        function: Decorator function that will divert
            stdout and stderr to logging streams.
    """

    def logger_decorator(func):
        """This is the actual decorator.

        Args:
            func (function): Function to decorate.

        Returns:
            function: Decorated function.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            stdout_logger = StreamLogger(stdout_writer)
            stderr_logger = StreamLogger(stderr_writer)
            with capture_output(stdout_logger, stderr_logger):
                return func(*args, **kwargs)
        return wrapper

    return logger_decorator

@contextmanager
def capture_output(stdout_writer=None, stderr_writer=None):
    """This function provides a with-context that will capture stdout
    and stderr from a call within the context.

    Args:
        stdout_writer (function): Logger function to use for stdout.
            Default is simple StringIO.
        stderr_writer (function): Logger function to use for stdout.
            Default is simple StringIO.


    Examples:

        with capture_output() as (out,err):
            print('test')
        print(out)
    """
    if stdout_writer is None:
        stdout_writer = StringIO()
    if stderr_writer is None:
        stderr_writer = StringIO()

    new_out, new_err = stdout_writer, stderr_writer
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err
