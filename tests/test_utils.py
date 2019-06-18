# -*- coding=utf-8 -*-
"""This class tests various features of the buildrules.common.utils-module."""

import unittest
import sys

from testfixtures import log_capture

from buildrules.common.utils import stdstreams_to_logger, capture_output

from .common import ignore_deprecationwarning

class TestUtils(unittest.TestCase):
    """This class tests various features of the buildrules.common.utils-module."""

    def test_stdout_without_capture(self):
        """ Test that capture_output will correctly capture stdout."""
        def test_print():
            print('test')

        with capture_output() as (out, _):
            test_print()

        output = out.getvalue().strip()
        self.assertEqual(output, 'test')

    def test_stderr_without_capture(self):
        """ Test that capture_output will correctly capture stderr."""
        def test_print():
            print('test', file=sys.stderr)

        with capture_output() as (_, err):
            test_print()

        err_output = err.getvalue().strip()
        self.assertEqual(err_output, 'test')

    @ignore_deprecationwarning
    @log_capture()
    def test_stdout_with_capture(self, capture):
        """ Test that stdstreams_to_logger will correctly capture stdout/stderr to logs."""
        def test_print():
            print('test')

        with capture_output() as (out, _):
            stdstreams_to_logger()(test_print)()

        output = out.getvalue().strip()
        self.assertEqual(output, '')

        capture.check(
            ('root', 'INFO', 'test'),
        )

    @ignore_deprecationwarning
    @log_capture()
    def test_stderr_with_capture(self, capture):
        """ Test that stdstreams_to_logger will correctly capture stdout/stderr to logs."""

        def test_print():
            print('test', file=sys.stderr)

        with capture_output() as (_, err):
            stdstreams_to_logger()(test_print)()

        err_output = err.getvalue().strip()
        self.assertEqual(err_output, '')

        capture.check(
            ('root', 'WARNING', 'test'),
        )



if __name__ == '__main__':
    unittest.main()
