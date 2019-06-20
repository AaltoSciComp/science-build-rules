# -*- coding: utf-8 -*-
"""SpackBuilder is a builder that builds using spack.
"""
import os
import logging

from buildrules.common.builder import Builder
from jinja2 import Template

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
        },
        'required': ['build_environment_repository']
    }]

    def __init__(self, conf_folder):
        self._build_folder = None
        super().__init__(conf_folder)

    def _clone_build_environment(self):
        """Clones build environment into a temporary directory"""
        git_url = self._confreader['build_config']['build_environment_repository']

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
        return []

if __name__ == "__main__":
    import sys

    CONF_FOLDER = sys.argv[1]

    CI_BUILDER = CIBuilder(CONF_FOLDER)
    CI_BUILDER.describe()
