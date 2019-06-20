# -*- coding=utf-8 -*-
"""These tests test various features of the buildrules.common.builder-module."""
import os
import unittest
import copy
import logging
from testfixtures import log_capture

from .common import (ignore_deprecationwarning, example_function,
                    count_log_events, EXAMPLE_CONFIGS, EXAMPLE_SCHEMAS)
from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, RuleError
from jsonschema.exceptions import ValidationError


def print_keys(conf_dict):
    """Prints the keys of a given dict."""
    for key in conf_dict:
        print(key)

class TestBuilder(unittest.TestCase):

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_empty_init(self):

        class TestBuilderEmptyInit(Builder):
            pass

        self.assertIsInstance(TestBuilderEmptyInit(os.path.join('tests', 'builder_test')), Builder)

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_error(self, capture):
        """This function tests the behaviour and the resulting output when
        buildrule produces an error."""

        class TestBuilderError(Builder):

            def __init__(self, conf_folder):
                self.rule_ran = False
                super().__init__(conf_folder)

            def good_function(self):
                return 1

            def good_function2(self):
                return 2

            def _get_rules(self):
                rules = [
                    PythonRule(
                        self.good_function,
                        [],
                        {}),
                    SubprocessRule(
                        ['false']
                    ),
                    PythonRule(
                        self.good_function2,
                        [],
                        {}),
                ]

                return rules

        builder_instance = TestBuilderError(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        with self.assertRaises(RuleError):
            builder_instance()

        event_counts = count_log_events(capture)

        # Check that there are only two info calls (third rule is not called)
        self.assertEqual(event_counts['INFO'], 2)

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_one_rule(self, capture):
        """This function tests the behaviour and the resulting output when creating
        a builder with one simple rule."""

        class TestBuilderOneRule(Builder):

            def __init__(self, conf_folder):
                self.rule_ran = False
                super().__init__(conf_folder)

            def run_rule(self):
                self.rule_ran = True

            def _get_rules(self):
                new_rule = PythonRule(
                    self.run_rule,
                    [],
                    {})
                return [new_rule]

        builder_instance = TestBuilderOneRule(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        self.assertFalse(builder_instance.rule_ran)
        builder_instance()
        self.assertTrue(builder_instance.rule_ran)

        capture.check(
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: '
                'TestBuilder.test_builder_one_rule.<locals>.TestBuilderOneRule.run_rule, '
                'args: [], kwargs: {} }'
            )
        )

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_describe(self, capture):
        """This function creates a simple builder, then checks the output from the
        Builder's 'describe()' method."""

        class TestBuilderDescribe(Builder):

            def _get_rules(self):
                return [
                    PythonRule(
                        example_function,
                        [0, 0],
                        {}),
                    SubprocessRule(
                        ['echo', 'test'])
                    ]

        builder_instance = TestBuilderDescribe(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        builder_instance.describe()

        capture.check(
            (
                'TestBuilderDescribe',
                'INFO',
                'Builder: None',
            ),
            (
                'TestBuilderDescribe',
                'INFO',
                'Configuration files: deployment_config.yaml',
            ),
            (
                'TestBuilderDescribe',
                'INFO',
                'Build rule descriptions:',
            ),
            (
                'TestBuilderDescribe',
                'INFO',
                'PythonRule: { function: example_function, args: [0, 0], kwargs: {} }'
            ),
            (
                'TestBuilderDescribe',
                'INFO',
                'SubprocessRule: { sp_function: echo test, env: None, shell: False }'
            ),
            (
                'TestBuilderDescribe',
                'INFO',
                'Deployment descriptions:'
            ),
        )

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_additional_conf_file_empty_schema(self, capture):
        """This function creates a simple builder with an additional configuration file,
        prints the keys in that configuration file and checks that the output is what's
        expected."""

        class TestBuilderAdditionalConfiguration(Builder):

            CONF_FILES = ['book.yaml']
            SCHEMAS = [{}]

            def _get_rules(self):
                new_rule = PythonRule(
                    print_keys,
                    [self._confreader['book']],
                    {})

                return [new_rule]

        builder_instance = TestBuilderAdditionalConfiguration(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        builder_instance()

        capture.check(
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: print_keys, '
                "args: [{'title': 'The Egyptian', 'author': {'last_name': 'Waltari', "
                "'first_name': 'Mika'}, 'isbn': '1-55652-441-2'}], kwargs: {} }"
            ),
            ('PythonRule', 'INFO', 'title'),
            ('PythonRule', 'INFO', 'author'),
            ('PythonRule', 'INFO', 'isbn')
        )

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_additional_conf_file_schema_valid(self, capture):
        """This function creates a simple builder with an additional configuration file and
        a schema for that configuration file. Then prints the keys in the configuration file
        and checks that the output is what's expected."""

        class TestBuilderAdditionalConfFileSchemaValid(Builder):

            CONF_FILES = ['book.yaml']
            SCHEMAS = [{
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"}
                        },
                        "required": ["first_name", "last_name"],
                        "maxProperties": 2
                    },
                    "isbn": {"type": "string"}
                },
                "required": ["title", "author", "isbn"],
                "maxProperties": 3
            }]

            def _get_rules(self):
                new_rule = PythonRule(
                    print_keys,
                    [self._confreader['book']],
                    {})

                return [new_rule]

        builder_instance = TestBuilderAdditionalConfFileSchemaValid(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        builder_instance()

        capture.check(
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: print_keys, '
                "args: [{'title': 'The Egyptian', 'author': {'last_name': 'Waltari', "
                "'first_name': 'Mika'}, 'isbn': '1-55652-441-2'}], kwargs: {} }"
            ),
            ('PythonRule', 'INFO', 'title'),
            ('PythonRule', 'INFO', 'author'),
            ('PythonRule', 'INFO', 'isbn')
        )

    def test_builder_additional_conf_file_schema_invalid(self):
        """This function creates a simple builder with an additional configuration file and
        a schema for that configuration file. The validation for the configuration file should
        fail."""

        class TestBuilderAdditionalConfFileSchemaInvalid(Builder):

            CONF_FILES = ['book.yaml']
            SCHEMAS = [{
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"}
                        },
                        "required": ["first_name", "last_name"],
                        "maxProperties": 2
                    },
                    "isbn": {"type": "string"}
                },
                "required": ["title", "author", "isbn", "NON-EXISTING_BUT_REQUIRED_FIELD"],
                "maxProperties": 3
            }]

        with self.assertRaises(ValidationError):
            builder_instance = TestBuilderAdditionalConfFileSchemaInvalid(os.path.join('tests', 'builder_test'))

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_two_addit_conf_files_one_schema(self, capture):
        """This function creates a simple builder with an additional conf_file, but only one non-empty
        schema, then prints keys of both configurations files and checks the output."""

        class TestBuilderTwoAdditConfFilesOneSchema(Builder):

            CONF_FILES = ['book.yaml', 'test.yaml']
            SCHEMAS = [
                {},
                {
                    "type": "object",
                    "properties": {
                        "boolean_test": {"type": "boolean"},
                        "string_test": {"type": "string"},
                        "number_test": {"type": "number"},
                        "filename": {"type": "string"}
                    },
                    "required": ["boolean_test", "string_test", "number_test", "filename"],
                    "maxProperties": 4
                }]

            def _get_rules(self):
                return [
                    PythonRule(
                        print_keys,
                        [self._confreader['book']],
                        {}),
                    PythonRule(
                        print_keys,
                        [self._confreader['test']],
                        {})
                    ]

        builder_instance = TestBuilderTwoAdditConfFilesOneSchema(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        builder_instance()

        capture.check(
            (
                'PythonRule',
                'INFO',
                "Running PythonRule: { function: print_keys, args: [{'title': 'The "
                "Egyptian', 'author': {'last_name': 'Waltari', 'first_name': 'Mika'}, "
                "'isbn': '1-55652-441-2'}], kwargs: {} }"
            ),
            ('PythonRule', 'INFO', 'title'),
            ('PythonRule', 'INFO', 'author'),
            ('PythonRule', 'INFO', 'isbn'),
            (
                'PythonRule',
                'INFO',
                "Running PythonRule: { function: print_keys, args: [{'boolean_test': True, "
                "'string_test': 'test', 'number_test': 1, 'filename': 'test.yaml'}], kwargs: "
                '{} }'
            ),
            ('PythonRule', 'INFO', 'boolean_test'),
            ('PythonRule', 'INFO', 'string_test'),
            ('PythonRule', 'INFO', 'number_test'),
            ('PythonRule', 'INFO', 'filename')
        )

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_two_addit_conf_files_two_schemas(self, capture):
        """This function creates a simple builder with an additional conf_file, but only one non-empty
        schema, then prints keys of both configurations files and checks the output."""

        class TestBuilderTwoAdditConfFilesTwoSchemas(Builder):

            CONF_FILES = ['book.yaml', 'test.yaml']
            SCHEMAS = [
                {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "author": {
                            "type": "object",
                            "properties": {
                                "first_name": {"type": "string"},
                                "last_name": {"type": "string"}
                            },
                            "required": ["first_name", "last_name"],
                            "maxProperties": 2
                        },
                        "isbn": {"type": "string"}
                    },
                    "required": ["title", "author", "isbn"],
                    "maxProperties": 3
                },
                {
                    "type": "object",
                    "properties": {
                        "boolean_test": {"type": "boolean"},
                        "string_test": {"type": "string"},
                        "number_test": {"type": "number"},
                        "filename": {"type": "string"}
                    },
                    "required": ["boolean_test", "string_test", "number_test", "filename"],
                    "maxProperties": 4
                }]

            def _get_rules(self):
                return [
                    PythonRule(
                        print_keys,
                        [self._confreader['book']],
                        {}),
                    PythonRule(
                        print_keys,
                        [self._confreader['test']],
                        {})
                    ]

        builder_instance = TestBuilderTwoAdditConfFilesTwoSchemas(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        builder_instance()

        capture.check(
            (
                'PythonRule',
                'INFO',
                "Running PythonRule: { function: print_keys, args: [{'title': 'The "
                "Egyptian', 'author': {'last_name': 'Waltari', 'first_name': 'Mika'}, "
                "'isbn': '1-55652-441-2'}], kwargs: {} }"
            ),
            ('PythonRule', 'INFO', 'title'),
            ('PythonRule', 'INFO', 'author'),
            ('PythonRule', 'INFO', 'isbn'),
            (
                'PythonRule',
                'INFO',
                "Running PythonRule: { function: print_keys, args: [{'boolean_test': True, "
                "'string_test': 'test', 'number_test': 1, 'filename': 'test.yaml'}], kwargs: "
                '{} }'
            ),
            ('PythonRule', 'INFO', 'boolean_test'),
            ('PythonRule', 'INFO', 'string_test'),
            ('PythonRule', 'INFO', 'number_test'),
            ('PythonRule', 'INFO', 'filename')
        )

    def test_builder_two_addit_conf_files_two_schemas_one_invalid(self):
        """This function creates a simple builder with an additional conf_file, but only one non-empty
        schema, then prints keys of both configurations files and checks the output."""

        class TestBuilderTwoAdditConfFilesTwoSchemasOneInvalid(Builder):

            CONF_FILES = ['book.yaml', 'test.yaml']
            SCHEMAS = [
                {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "author": {
                            "type": "object",
                            "properties": {
                                "first_name": {"type": "string"},
                                "last_name": {"type": "string"}
                            },
                            "required": ["first_name", "last_name"],
                            "maxProperties": 2
                        },
                        "isbn": {"type": "string"}
                    },
                    "required": ["title", "author", "isbn", "NON-EXISTING_BUT_REQUIRED_FIELD"],
                    "maxProperties": 3
                },
                {
                    "type": "object",
                    "properties": {
                        "boolean_test": {"type": "boolean"},
                        "string_test": {"type": "string"},
                        "number_test": {"type": "number"},
                        "filename": {"type": "string"}
                    },
                    "required": ["boolean_test", "string_test", "number_test", "filename"],
                    "maxProperties": 4
                }]

        with self.assertRaises(ValidationError):
            builder_instance = TestBuilderTwoAdditConfFilesTwoSchemasOneInvalid(os.path.join('tests', 'builder_test'))

    @ignore_deprecationwarning
    @log_capture(level=logging.INFO)
    def test_builder_dry_run(self, capture):
        """This function tests a 'dry run' of a build."""

        class TestBuilderDryRun(Builder):
            def __init__(self, conf_folder):
                self.rule_ran = False
                super().__init__(conf_folder)

            def run_rule(self):
                self.rule_ran = True

            def _get_rules(self):
                new_rule = PythonRule(
                    self.run_rule,
                    [],
                    {})
                return [new_rule]

        builder_instance = TestBuilderDryRun(os.path.join('tests', 'builder_test'))
        self.assertIsInstance(builder_instance, Builder)
        self.assertFalse(builder_instance.rule_ran)
        builder_instance(dry_run=True)
        self.assertFalse(builder_instance.rule_ran)

        capture.check(
            (
                'PythonRule',
                'INFO',
                'Running PythonRule: { function: '
                'TestBuilder.test_builder_dry_run.<locals>.TestBuilderDryRun.run_rule, '
                'args: [], kwargs: {} }'
            )
        )
