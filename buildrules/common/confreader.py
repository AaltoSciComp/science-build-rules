# -*- coding=utf-8 -*-
"""This module contains ConfReader class that contains methods for reading
and validating different yaml files."""
from os.path import basename, splitext
from collections.abc import Mapping
from textwrap import indent
from copy import copy
from jsonschema import validate, Draft4Validator
import yaml

class ConfReader(Mapping):
    """ConfReader is used for reading an validating configurations.

    Args:
        yamlfiles (list): YAML files to load into configuration.
        schemas (list): A list of schemas that correspond to YAMLs.
    """

    def __init__(self, yamlfiles, schemas):
        self._configs = dict()
        self._conf_files = copy(yamlfiles)
        for yamlfile, schema in zip(yamlfiles, schemas):

            # Read data from configuration file
            data = self._read_yaml(yamlfile)

            # Insert configuration to self._configs
            conf_key = splitext(basename(yamlfile))[0]
            self._configs[conf_key] = data

            # Validate configuration
            self.validate(conf_key, schema)

    def __getitem__(self, confname):
        """Get a configuration.

        Args:
            confname (str): Configuration name to return.

        Returns:
            object: Returned configuration.
        """
        return self._configs[confname]

    def get(self, confname, default=None):
        """Get a configuration.

        Args:
            confname (str): Configuration name to return.
            default (object): Optional default argument.

        Returns:
            object: Returned configuration.
        """
        return self._configs.get(confname, default)

    def __iter__(self):
        """Get an iterator that goes over different configuration
        files.

        Returns:
            iter: Returned iterator.
        """
        return iter(self._configs)

    def __len__(self):
        """Returns the number of configuration files available.

        Returns:
            int: Number of configuration files stored.
        """
        return len(self._configs)

    def validate(self, config, schema):
        """Validates that the data matches the schema.

        Args:
            config (object): Configuration to validate.
            schema (dict): Schema used for validation.
        Raises:
            ValidationError: Raises ValidationError if data does not match
                the schema.
        """
        validate(instance=self[config], schema=schema)

    def _read_yaml(self, yamlfile):
        """
        Reads in a yamlfile. If template is provided, will check that the
        yaml matches with the template.
        """

        with open(yamlfile, 'r') as yaml_f:
            configuration = yaml.load(yaml_f.read(), Loader=yaml.Loader)

        return configuration

    def __str__(self):

        conf_files = [config for config in self._conf_files]
        configs = [indent(yaml.dump(self[config], default_flow_style=False), 4*' ')
                   for config in iter(self)]


        outputs = ['{0}:\n\n{1}'.format(conf_file, config)
                   for conf_file, config in zip(conf_files, configs)]

        output_str = 'ConfReader with {0} configuration files:\n\n'.format(len(self))
        output_str += '\n'.join(outputs)

        return output_str
