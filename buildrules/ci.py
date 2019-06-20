# -*- coding: utf-8 -*-
"""SpackBuilder is a builder that builds using spack.
"""
import os
import logging
import tempfile
from jinja2 import Template

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule

class CIBuilder(Builder):

    """CIBuilder extends on Builder and creates CI environment for running buildrules.
    """
    BUILDER_NAME = 'CI'
    CONF_FILES = ['build_config.yaml']
    SCHEMAS = [{
        '$schema': 'http://json-schema.org/schema#',
        'title': 'CI environment schema',
        'type': 'object',
        'additionalProperties': False,
        'patternProperties': {
            'build_environment_repository': {'type': 'string'},
            'build_folder': {'type': 'string'},
            'skip_rules': {
                'type': 'array',
                'default': [],
                'items': {
                    'type': 'string'
                },
            },
        },
        'required': ['build_environment_repository','build_folder']
    }]

    def _clone_build_environment_repo(self):
        """Clones build environment into a temporary directory"""
        if not self._skip_rule('clone_environment_repository'):
            src = self._confreader['build_config']['build_environment_repository']
            dest = self._confreader['build_config']['build_folder']
            return [SubprocessRule(
                ['git',
                 'clone',
                 '--depth=1',
                 src,
                 dest,
                '2>&1'],
                shell=True)]
        return []

    def _create_nfs_directories(self):
        """Creates directories for nfs"""


    def _fill_template(self, template):
        """Fills a jinja2-template based on build_config.
        
        Args:
            template (str): jinja2-template as a string.
        Returns:
            str: Filled template.
        """
        return Template(template).render(self._confreader['build_config'])


    def _get_rules(self):
        rules = []
        rules.extend(self._clone_build_environment_repo())
        return rules

if __name__ == "__main__":
    import sys

    CONF_FOLDER = sys.argv[1]

    CI_BUILDER = CIBuilder(CONF_FOLDER)
    CI_BUILDER.describe()
