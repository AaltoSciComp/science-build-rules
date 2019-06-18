# -*- coding=utf-8 -*-
"""These tests test various features of the buildrules.common.confreader-module."""

import os
import copy
import unittest
from jsonschema.exceptions import ValidationError

from buildrules.common.confreader import ConfReader
from .common import EXAMPLE_CONFIGS, EXAMPLE_SCHEMAS

class TestConfReader(unittest.TestCase):
    """This class tests various features of the buildrules.common.confreader-module."""

    def test_conf_reader_valid_default(self):
        """This function tests behaviour of ConfReader when
        configuration schema matches the configuration."""

        deployment_config = EXAMPLE_CONFIGS['deployment_config']
        deployment_config_schema = copy.deepcopy(EXAMPLE_SCHEMAS['deployment_config'])

        cr_valid = ConfReader(
            [deployment_config],
            [deployment_config_schema]
        )
        self.assertIsInstance(cr_valid, ConfReader)
        self.assertEqual(cr_valid['deployment_config']['method'], 'rsync')

    def test_conf_reader_valid_extra_field(self):
        """This function tests behaviour of ConfReader when
        the configuration schema allows a field that is not defined
        in properties and the configuration contains
        such a field (here: "method")."""

        deployment_config = EXAMPLE_CONFIGS['deployment_config']
        deployment_config_schema = copy.deepcopy(EXAMPLE_SCHEMAS['deployment_config'])
        del deployment_config_schema['properties']['method']
        deployment_config_schema['required'] = ["delete", "set_sbit", "target_host"]

        cr_valid = ConfReader(
            [deployment_config],
            [deployment_config_schema]
        )
        self.assertIsInstance(cr_valid, ConfReader)
        self.assertEqual(cr_valid['deployment_config']['method'], 'rsync')


    def test_conf_reader_valid_nested_default(self):
        """This function tests behaviour of ConfReader when
        configuration schema contains nested fields and the
        schema matches the configuration."""
        book_schema = {
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
        }

        cr_valid = ConfReader([os.path.join('tests', 'examples', 'book.yaml')], [book_schema])
        self.assertIsInstance(cr_valid, ConfReader)
        self.assertEqual(cr_valid['book']['author']['last_name'], 'Waltari')


    def test_conf_reader_valid_nested_extra_field(self):
        """This function tests behaviour of ConfReader when
        the configuration schema allows a nested field that is not defined
        in properties and the configuration contains
        such a field (here: "author": "last_name")."""
        book_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "author": {
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string"},
                    },
                    "required": ["first_name"],
                    "maxProperties": 2
                },
                "isbn": {"type": "string"}
            },
            "required": ["title", "author", "isbn"],
            "maxProperties": 3
        }

        cr_valid = ConfReader(
            [os.path.join('tests', 'examples', 'book.yaml')],
            [book_schema]
        )
        self.assertIsInstance(cr_valid, ConfReader)
        self.assertEqual(cr_valid['book']['author']['last_name'], 'Waltari')

    def test_conf_reader_invalid_missing_field(self):
        """This function tests behaviour of ConfReader when
        a required field is missing from the configuration."""

        deployment_config_schema = copy.deepcopy(EXAMPLE_SCHEMAS['deployment_config'])
        deployment_config_schema["properties"]["important_extra_field"] = {"type": "string"}
        deployment_config_schema["required"] = [
            "method",
            "delete",
            "set_sbit",
            "target_host",
            "important_extra_field"
        ]
        deployment_config_schema["maxProperties"] = 5

        with self.assertRaises(ValidationError):
            cr_invalid = ConfReader(
                [os.path.join('tests', 'examples', 'deployment_config.yaml')],
                [deployment_config_schema])
            print(cr_invalid)

    def test_conf_reader_invalid_wrong_field_type(self):
        """This function tests behaviour of ConfReader when
        a required field has the wrong type."""
        deployment_config_schema = {
            "type": "object",
            "properties": {
                "method": {"type": "string"},
                "delete": {"type": "boolean"},
                "set_sbit": {"type": "number"},
                "target_host": {"type": "string"},
            },
            "required": ["method", "delete", "set_sbit", "target_host"],
            "maxProperties": 4
        }
        with self.assertRaises(ValidationError):
            cr_invalid = ConfReader(
                [os.path.join('tests', 'examples', 'deployment_config.yaml')],
                [deployment_config_schema])
            print(cr_invalid)

    def test_conf_reader_invalid_extra_field(self):
        """This function tests behaviour of ConfReader when
        the configuration schema doesn't allow fields other than
        those defined in properties and the configuration contains
        such a field (here: "method")."""
        deployment_config_schema = {
            "type": "object",
            "properties": {
                "delete": {"type": "boolean"},
                "set_sbit": {"type": "number"},
                "target_host": {"type": "string"},
            },
            "required": ["delete", "set_sbit", "target_host"],
            "maxProperties": 3
        }
        with self.assertRaises(ValidationError):
            cr_invalid = ConfReader(
                [os.path.join('tests', 'examples', 'deployment_config.yaml')],
                [deployment_config_schema])
            print(cr_invalid)

    def test_conf_reader_invalid_field_typo(self):
        """This function tests behaviour of ConfReader when
        the configuration schema requires exact fields and
        the configuration contains a typo (here, schema requires
        "deleted", but configuration has "delete")."""
        deployment_config_schema = {
            "type": "object",
            "properties": {
                "method": {"type": "string"},
                "deleted": {"type": "boolean"},
                "set_sbit": {"type": "boolean"},
                "target_host": {"type": "string"},
            },
            "required": ["method", "deleted", "set_sbit", "target_host"],
            "maxProperties": 4
        }
        with self.assertRaises(ValidationError):
            cr_invalid = ConfReader(
                [os.path.join('tests', 'examples', 'deployment_config.yaml')],
                [deployment_config_schema]
            )
            print(cr_invalid)

    def test_conf_reader_invalid_nested_field_missing(self):
        """This function tests behaviour of ConfReader when
        a required nested field is missing from the
        configuration (here: "author": "year_of_birth" is missing)."""
        book_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "author": {
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "year_of_birth": {"type": "number"}
                    },
                    "required": ["first_name", "last_name", "year_of_birth"],
                    "maxProperties": 3
                },
                "isbn": {"type": "string"}
            },
            "required": ["title", "author", "isbn"],
            "maxProperties": 3
        }

        with self.assertRaises(ValidationError):
            cr_invalid = ConfReader(
                [os.path.join('tests', 'examples', 'book.yaml')],
                [book_schema]
            )
            print(cr_invalid)


if __name__ == '__main__':
    unittest.main()
