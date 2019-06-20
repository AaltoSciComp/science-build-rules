# -*- coding=utf-8 -*-
"""These tests test various features of the buildrules.common.rule-module."""

import unittest
import logging
from testfixtures import log_capture
from subprocess import CalledProcessError

from buildrules.common.rule import PythonRule, SubprocessRule, RuleError, LoggingRule

from .common import ignore_deprecationwarning, example_function

class TestRule(unittest.TestCase):
    """This class tests various features of the buildrules.common.rule-module."""

    @ignore_deprecationwarning
    @log_capture()
    def test_python_rule(self, capture):
        """This function tests behaviour of the class buildrules.common.rule.PythonRule."""
        self.assertEqual(
            PythonRule(
                example_function,
                [],
                {},
                stdout_writer=logging.info,
                stderr_writer=logging.warning)(), 3)
        self.assertEqual(
            PythonRule(
                example_function,
                [3, 4],
                {},
                stdout_writer=logging.info,
                stderr_writer=logging.warning)(), 7)
        self.assertEqual(
            PythonRule(
                example_function,
                [5],
                {'val2': 6},
                stdout_writer=logging.info,
                stderr_writer=logging.warning)(), 11)
        self.assertEqual(
            PythonRule(
                example_function,
                [],
                {'val1': 7, 'val2': 8},
                stdout_writer=logging.info,
                stderr_writer=logging.warning)(), 15)
        self.assertEqual(
            PythonRule(
                example_function,
                [],
                {},
                stdout_writer=logging.warning,
                stderr_writer=logging.warning)(), 3)

        capture.check(
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: '
                'example_function, args: [], '
                'kwargs: {} }'
            ),
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: '
                'example_function, args: [3, '
                '4], kwargs: {} }'
            ),
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: '
                'example_function, args: [5], '
                "kwargs: {'val2': 6} }"
            ),
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: '
                'example_function, args: [], '
                "kwargs: {'val1': 7, 'val2': 8} }"
            ),
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: '
                'example_function, args: [], '
                'kwargs: {} }'
            )
        )

    @ignore_deprecationwarning
    @log_capture()
    def test_subprocess_rule(self, capture):
        """This function tests behaviour of the class buildrules.common.rule.SubprocessRule."""
        sp1 = SubprocessRule(
                ['echo'],
                stdout_writer=logging.info,
                stderr_writer=logging.warning)()
        sp2 = SubprocessRule(
                ['echo', 'a', 'b'],
                stdout_writer=logging.info,
                stderr_writer=logging.warning)()
        sp3 = SubprocessRule(
                ['echo $TEST'],
                {'TEST': 'test'},
                shell=True,
                stdout_writer=logging.info,
                stderr_writer=logging.warning)()

        capture.check(
            (
                'SubprocessRule',
                'INFO',
                'Running SubprocessRule: { sp_function: '
                "echo, "
                'env: None, '
                'shell: False }'
            ),
            (
                'SubprocessRule',
                'INFO',
                'Running SubprocessRule: { sp_function: '
                "echo a b, "
                'env: None, '
                'shell: False }'
            ),
            (
                'root',
                'INFO',
                "a b"
            ),
            (
                'SubprocessRule',
                'INFO',
                'Running SubprocessRule: { sp_function: '
                "echo $TEST, "
                "env: {'TEST': 'test'}, "
                'shell: True }'
            ),
            (
                'root',
                'INFO',
                "test"
            ),
        )
    @ignore_deprecationwarning
    @log_capture()
    def test_subprocess_rule_error(self, capture):
        with self.assertRaises(RuleError):
            SubprocessRule(
                ['abcdefghijk'],
                stdout_writer=logging.info,
                stderr_writer=logging.warning)()
        with self.assertRaises(RuleError):
            SubprocessRule(
                ['false'],
                stdout_writer=logging.info,
                stderr_writer=logging.warning)()


    @ignore_deprecationwarning
    @log_capture()
    def test_python_rule_dry_run(self, capture):
        pr = PythonRule(
                example_function,
                [],
                {},
                stdout_writer=logging.info,
                stderr_writer=logging.warning)(dry_run=True)
        capture.check(
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: example_function, args: [], kwargs: {} }'
            ),
        )

    @ignore_deprecationwarning
    @log_capture()
    def test_subprocess_dry_run(self, capture):
        sp = SubprocessRule(
                ['echo', 'test'],
                stdout_writer=logging.info,
                stderr_writer=logging.warning)(dry_run=True)
        capture.check(
            (
                'SubprocessRule',
                'INFO',
                'Running SubprocessRule: { sp_function: echo test, env: None, shell: False '
                '}'
            ),
        )

    @ignore_deprecationwarning
    @log_capture()
    def test_loggingrule(self, capture):
        LoggingRule("test")()

        capture.check(
            (
                'LoggingRule',
                'INFO',
                'test'
            )
        )

if __name__ == '__main__':
    unittest.main()
