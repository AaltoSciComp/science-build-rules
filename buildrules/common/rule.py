# -*- coding: utf-8 -*-
"""This module defines build rules that are called to do individual build steps.

Build rules are individual job steps of the build. Each of them can contains a string
method that describes the contents of the buildrule. Each of them can be called and
the output of the build rule should go through logging. Possible Exceptions should be
returned as BuildRuleErrors.
"""

import os
import logging
import subprocess
import select
import traceback
from io import StringIO

class RuleError(Exception):
    """BuildRuleError is the error for build rules."""

def rule_error_wrapper(function):
    """buildrule_error_wrapper is a decorator that logs errors, prints
    stack trace and returns a BuildRuleError instead of normal Exception

    Args:
        function (function): Function that will be decorated.

    Returns:
        exception_wrapper: Decorated function.
    """

    def exception_wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except KeyboardInterrupt as error:
            raise error
        except Exception as error:
            logging.error('Encountered an error:')
            trace = StringIO()
            traceback.print_stack(file=trace)
            logging.error(trace.getvalue())
            trace.close()
            raise RuleError(error) from error
    return exception_wrapper


class Rule:
    """BuildRule is created by ConfReader and it is used by
    Builder to build software.

    Args:
        stdout_writer (function): Function to use for logging stdout from command.
        stderr_writer (function): Function to use for logging stderr from command.
    """

    def __init__(self, stdout_writer, stderr_writer):
        self._logger = logging.getLogger(self.__class__.__name__)
        if stdout_writer is None:
            stdout_writer = self._logger.info
        if stderr_writer is None:
            stderr_writer = self._logger.error
        self._stdout_writer = stdout_writer
        self._stderr_writer = stderr_writer

    def __repr__(self):
        return self.__str__()

    def __call__(self):
        return False

class PythonRule(Rule):
    """PythonRule is a BuildRule that when called will execute a Python
    command.

    Args:
        func (function): Function that will be executed.
        args (list): List of arguments for command. Default is empty list.
        kwargs (dict): Dictionary of keyword arguments for the command. Default
            is empty dictionary.
        stdout_writer (function, optional): Function to use for logging stdout
            from command. Default is logging.info.
        stderr_writer (function, optional): Function to use for logging stderr
            from command. Default is logging.warning.

    Returns:
        output (object): Output of the Python function call.
    """

    def __init__(self,
                 func,
                 args=None,
                 kwargs=None,
                 stdout_writer=None,
                 stderr_writer=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        self._func = func
        self._args = args
        self._kwargs = kwargs
        super().__init__(stdout_writer, stderr_writer)

    @rule_error_wrapper
    def __call__(self, dry_run=False):
        self._logger.info('Running %s', self)

        if not dry_run:
            return self._func(*self._args, **self._kwargs)

        return False

    def __str__(self):
        return 'PythonRule: {{ function: {0}, args: {1}, kwargs: {2} }}'.format(
            self._func.__qualname__,
            self._args,
            self._kwargs)

class SubprocessRule(Rule):
    """SubprocessRule is a BuildRule that when called will execute a shell
    command using Subprocess

    Args:
        sp_command (list): Command in subprocess list form.
        env (dict, optional): Dictionary of extra environment variables for
            the subprocess call.
        shell (boolean, optional): Launch the subprocess in its own shell.
            Default is False.
        check (boolean, optional): Check for errors during the subprocess call.
            Default is True.
        stdout_writer (function, optional): Function to use for logging stdout
            from command. Default is logging.info.
        stderr_writer (function, optional): Function to use for logging stderr
            from command. Default is logging.warning.

    Returns:
        return_code (int): Return code of the subprocess call.

    """

    def __init__(self,
                 sp_command,
                 env=None,
                 shell=False,
                 check=True,
                 stdout_writer=None,
                 stderr_writer=None,
                 cwd=None):
        self._sp_command = sp_command
        self._orig_env = env
        if env is not None:
            current_env = os.environ.copy()
            current_env.update(env)
            env = current_env
        self._env = env
        self._shell = shell
        self._check = check
        self._cwd = cwd
        super().__init__(stdout_writer, stderr_writer)

    @rule_error_wrapper
    def __call__(self, dry_run=False):
        self._logger.info('Running %s', self)

        if self._shell:
            cmd = [' '.join(self._sp_command)]
        else:
            cmd = self._sp_command

        def logged_call():
            def capture_io():
                pass
            try:
                sp_call = subprocess.Popen(
                    cmd,
                    bufsize=0,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=self._env,
                    shell=self._shell,
                    cwd=self._cwd
                )

                loggers = {sp_call.stdout: self._stdout_writer,
                           sp_call.stderr: self._stderr_writer}

                def capture_io():
                    output = select.select([sp_call.stdout, sp_call.stderr], [], [], 1000)[0]
                    for io_stream in output:
                        line = io_stream.readline()[:-1].decode('utf-8')
                        if line:
                            loggers[io_stream](line)

                # Poll subprocess call for output
                while sp_call.poll() is None:
                    capture_io()

                capture_io()

                # Raise error if check is enabled
                return_code = sp_call.wait()
                if self._check and return_code != 0:
                    raise subprocess.CalledProcessError(return_code, ' '.join(cmd))
                return return_code

            finally:
                capture_io()

        if not dry_run:
            return logged_call()

        return 0

    def __str__(self):
        return 'SubprocessRule: {{ sp_function: {0}, env: {1}, shell: {2} }}'.format(
            ' '.join(self._sp_command),
            self._orig_env,
            self._shell)

class LoggingRule(Rule):
    """LoggingRule is a simple logger that outputs a message at desired step.

    Args:
        message (str): Message to output
        stdout_writer (function): Function to use for logging the message.
    """

    def __init__(self, message, stdout_writer=None):
        self._message = message
        super().__init__(stdout_writer, None)

    def __call__(self, dry_run=False):
        self._stdout_writer(self._message)

    def __str__(self):
        return 'LoggingRule: "{0}"'.format(self._message)
