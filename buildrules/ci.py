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
            'science_build_rules_repository': {'type': 'string'},
            'build_folder': {'type': 'string'},
            'compose_project_name': {'type': 'string'},
            'buildbot_master': {
                'type': 'object',
                'properties': {
                    'image': {'type': 'string'},
                    'gitlab_hook_secret': {'type': 'string'},
                    'worker_password': {'type': 'string'},
                    'worker_port': {'type': 'integer'},
                    'web_url': {'type': 'string'},
                    'web_port': {'type': 'integer'},
                    'timeout': {'type': 'integer'},
                    'worker_uid': {'type': 'integer'},
                },
                'required': [
                    'image',
                    'worker_password',
                    'web_url',
                    'worker_uid'
                ],
            },
            'buildbot_db': {
                'type': 'object',
                'properties': {
                    'postgres_password': {'type': 'string'},
                },
            },
            'builds': {
                'type': 'object',
                'properties': {
                    'spack': {
                        'type': 'object',
                        'properties': {
                            'enabled': {'type': 'boolean'},
                        },
                        'required': ['enabled'],
                    },
                    'singularity': {
                        'type': 'object',
                        'properties': {
                            'enabled': {'type': 'boolean'},
                            'enable_portus_hook': {'type': 'boolean'},
                        },
                        'required': ['enabled'],
                    },
                    'registry_clone': {
                        'type': 'object',
                        'properties': {
                            'enabled': {'type': 'boolean'},
                        },
                        'required': ['enabled'],
                    },
                },
            },
            'target_workers': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'image:': {'type': 'string'},
                    },
                    'required': ['name', 'image'],
                },
            },
            'skip_rules': {
                'type': 'array',
                'default': [],
                'items': {
                    'type': 'string'
                },
            },
        },
        'required': [
            'build_environment_repository',
            'build_folder',
            'buildbot_master',
            'buildbot_db',
        ],
    }]

    def __init__(self, conf_folder):

        super().__init__(conf_folder)
        self._build_folder = self._confreader['build_config']['build_folder']
        self._conf_folder = os.path.join(
            self._confreader['build_config']['build_folder'],
            'configs')
        self._templates_folder = os.path.join(
            self._confreader['build_config']['build_folder'],
            'templates')

    def _get_clone_build_environment_rule(self):
        """Clones build environment into a temporary directory"""
        if not self._skip_rule('clone_environment_repository'):
            src = self._confreader['build_config']['build_environment_repository']
            dest = self._build_folder
            return [
                LoggingRule('Cloning build environment repository'),
                SubprocessRule(
                    ['git',
                     'clone',
                     '--depth=1',
                     src,
                     dest,
                     '2>&1'],
                    shell=True
                )
            ]
        return []

    def _get_config_creation_rules(self):
        return [
            LoggingRule('Creating buildbot_master.cfg'),
            PythonRule(
                self._write_template,
                args=[
                    os.path.join(
                        self._conf_folder,
                        'buildbot',
                        'buildbot_master.cfg'
                    ),
                    os.path.join(
                        self._templates_folder,
                        'buildbot_master.cfg.j2'
                    ),
                ],
            ),
            LoggingRule('Creating docker-compose.yml'),
            PythonRule(
                self._write_template,
                args=[
                    os.path.join(
                        self._build_folder,
                        'docker-compose.yml'
                    ),
                    os.path.join(
                        self._templates_folder,
                        'docker-compose.yml.j2'
                    ),
                ],
            ),
        ]


    def _create_nfs_directories(self):
        """Creates directories for nfs"""

    def _write_template(self, config_path, template_path):
        """Fills buildbot configuration"""
        with open(template_path, 'r') as template_file:
            template = ''.join(template_file.readlines())
        filled_template = self._fill_template(template)
        with open(config_path, 'w') as configuration_file:
            configuration_file.write(filled_template)

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
        rules.extend(self._get_clone_build_environment_rule())
        rules.extend(self._get_config_creation_rules())
        return rules

if __name__ == "__main__":
    import sys

    CONF_FOLDER = sys.argv[1]

    CI_BUILDER = CIBuilder(CONF_FOLDER)
    CI_BUILDER.describe()
