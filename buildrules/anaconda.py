# -*- coding: utf-8 -*-
"""AnacondaBuilder is a builder that builds using anaconda.
"""
import sys
import re
import os
import shutil
import logging
from glob import glob
import yaml

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule

class AnacondaBuilder(Builder):
    """AnacondaBuilder extends on Builder and creates buildrules for Anaconda build.
    """

    BUILDER_NAME = 'Spack'
    CONF_FILES = ['config.yaml', 'build_config.yaml']
    SCHEMAS = [
        {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Anaconda configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                'config': {
                    'type': 'object',
                    'default': {},
                    'properties': {
                        'install_tree': {'type': 'string'},
                        'build_stage': {
                            'oneOf': [
                                {'type': 'string'},
                                {'type': 'array',
                                 'items': {'type': 'string'}}],
                        },
                        'module_path': {'type': 'string'},
                        'source_cache': {'type': 'string'},
                    },
                },
            },
        }, {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Package configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                'environments': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'miniconda': {'type': 'boolean'},
                            'installer_version': {'type': 'string'},
                            'pip_packages': {
                                'default' : [],
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'conda_packages': {
                                'default' : [],
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                        },
                        'required': ['name', 'version'],
                    },
                },
            },
        }]


    def __init__(self, conf_folder):
        self._conda_path = os.path.join(os.getcwd(), 'conda')
        super().__init__(conf_folder)

    def _get_path(self, path_name):
        path_config = {
            'install_path': '$conda/opt/conda/software',
            'module_path': '$conda/opt/conda/modules',
            'source_cache': '$conda/var/conda/cache',
            'build_stage': '$conda/var/conda/stage',
        }
        path_config.update(self._confreader['config']['config'])
        return re.sub('\$conda', self._conda_path, path_config[path_name])

    def _get_directory_creation_rules(self):
        rules = []

        install_path = self._get_path('install_path')
        build_stage = self._get_path('build_stage')

        rules.extend([
            LoggingRule('Creating stage directory: %s' % build_stage),
            LoggingRule('Creating installation directory: %s' % build_stage)
        ])

        return rules

    def _get_environment_install_rules(self):
        rules = []

        install_tree = self._get_path('build_stage')
        build_stage = self._get_path('build_stage')

        for environments in self._confreader['build_config']['environments']:
            pass
        
        return rules

    def _get_rules(self):
        """_get_rules provides build rules for the builder.

        Anaconda build consists of the following steps:

        """

        rules = (
            self._get_directory_creation_rules() +
            self._get_environment_install_rules()
        )
        return rules

if __name__ == "__main__":

    CONF_FOLDER = sys.argv[1]

    ANACONDA_BUILDER = SpackBuilder(CONF_FOLDER)
    ANACONDA_BUILDER.describe()
