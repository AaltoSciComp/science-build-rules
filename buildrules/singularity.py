# -*- coding: utf-8 -*-
"""SingularityBuilder is a builder that builds using singularity.
"""
import sys
import re
import os
import shutil
import logging
from glob import glob
import yaml
import copy
import requests
import sh

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule

class SingularityBuilder(Builder):
    """SingularityBuilder extends on Builder and creates buildrules for Singularity build.
    """

    BUILDER_NAME = 'Singularity'
    CONF_FILES = ['config.yaml', 'build_config.yaml']
    SCHEMAS = [
        {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Singularity configuration file schema',
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
                'definitions': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'path': {'type': 'string'},
                            'fakeroot': {'type': 'boolean', 'default': False},
                        },
                        'required': ['name'],
                    },
                },
            },
        }]


    def __init__(self, conf_folder):
        self._singularity_path = os.path.join(os.getcwd(), 'singularity')
        super().__init__(conf_folder)
        self._source_cache = self._get_path('source_cache')
        self._build_stage = self._get_path('build_stage')
        self._install_path = self._get_path('install_path')
        self._module_path = self._get_path('module_path')
        self._installed_file = os.path.join(self._install_path, 'installed_images.yml')

    def _get_path(self, path_name):
        path_config = {
            'install_path': '$singularity/opt/singularity/software',
            'module_path': '$singularity/opt/singularity/modules',
            'source_cache': '$singularity/var/singularity/cache',
            'build_stage': '$singularity/var/singularity/stage',
        }
        path_config.update(self._confreader['config']['config'])
        return re.sub('\$singularity', self._singularity_path, path_config[path_name])

    def _get_directory_creation_rules(self):
        rules = []

        rules.extend([
            LoggingRule('Creating cache directory: %s' % self._source_cache),
            PythonRule(self._makedirs, [self._source_cache, 0o755]),
            LoggingRule('Creating stage directory: %s' % self._build_stage),
            PythonRule(self._makedirs, [self._build_stage, 0o755]),
            LoggingRule('Creating installation directory: %s' % self._install_path),
            PythonRule(self._makedirs, [self._install_path, 0o755]),
            LoggingRule('Creating module directory: %s' % self._module_path),
            PythonRule(self._makedirs, [self._module_path, 0o755]),
        ])

        return rules

    def _create_image_config(self, image_dict):
        default_config = {
            'installer_version': 'latest',
        }

        config = copy.deepcopy(default_config)
        config.update(image_dict)
        if 'module_name' not in config:
            config['module_name'] = config['name']
        if 'module_version' not in config:
            config['module_version'] = '{name}-{installer_version}'.format(**config)
        config['image_name'] = '{module_name}/{module_version}'.format(**config)

        return config

    def _get_installer_path(self, install_config):

        installer_fmt = "singularity-{installer_version}.tar.gz"

        installer = os.path.join(self._source_cache, installer_fmt.format(**install_config))

        return installer


    def _get_stage_path(self, stage_config):
        stage_path = os.path.join(
            self._build_stage,
            stage_config['module_name'],
            stage_config['module_version'])
        return stage_path

    def _get_install_path(self, install_config):
        install_path = os.path.join(
            self._install_path,
            install_config['module_name'],
            install_config['module_version'])
        return install_path

    def _prepare_installation_paths(self, module_name, module_version):

        stage_root = os.path.join(
            self._build_stage, module_name)
        if not os.path.isdir(stage_root):
            self._makedirs(stage_root, 0o755)
        stage_path = os.path.join(stage_root, module_version)
        if os.path.isdir(stage_path):
            self._logger.info((
                "Cleaning previous stage path: %s"), stage_path)
            shutil.rmtree(stage_path)

        install_root = os.path.join(
            self._install_path, module_name)
        if not os.path.isdir(install_root):
            self._makedirs(install_root, 0o755)

        module_root = os.path.join(
            self._module_path, module_name)
        if not os.path.isdir(module_root):
            self._makedirs(module_root, 0o755)

    def _get_installed_images(self):
        imgdir = self._install_path
        images = glob(os.path.join(imgdir, '*.sif'))
        return images

    def _update_installed_images(self, image_name, installation_config):
        installed_dict = self._get_installed_images()
        installed_dict['images'][image_name] = installation_config
        with open(self._installed_file, 'w') as installed_file:
            installed_file.write(
                yaml.dump(
                    installed_dict,
                    default_flow_style=False,
                    Dumper=yaml.SafeDumper
                ))

    def _get_image_install_rules(self):
        rules = []

        installed_images = self._get_installed_images()

        env_path = list(filter(
            lambda x: re.search('^/usr',x),
            os.getenv('PATH').split(':')))

        for definition in self._confreader['build_config']['definitions']:
            config = self._create_image_config(definition)

            installer = self._get_installer_path(config)
            stage_path = self._get_stage_path(config)
            install_path = self._get_install_path(config)

            if config['name'] not in installed_images:
                env_path_image = {
                    'PATH': ':'.join([os.path.join(stage_path, 'bin')] + env_path)
                }
                rules.extend([
                    LoggingRule((
                        "Image {{name}} not found.\n"
                        "Installing singularity image '{name}' with "
                        "module '{image_name}'").format(**config)),
                    PythonRule(
                        self._prepare_installation_paths,
                        [config['module_name'], config['module_version']]),
                    SubprocessRule(['bash', installer, '-b', '-p', stage_path], shell=True),
                ])
                rules.extend([
                    SubprocessRule(
                        ['singularity', 'list'],
                        env=env_path_image,
                        shell=True)
                ])
            #rules.append(
            #    PythonRule(
            #        self._update_installed_images,
            #        [config['name'], config]))

        return rules

    def _get_rules(self):
        """_get_rules provides build rules for the builder.

        Singularity build consists of the following steps:

        """

        rules = (
            self._get_directory_creation_rules() +
            self._get_image_install_rules()
        )
        return rules

if __name__ == "__main__":

    CONF_FOLDER = sys.argv[1]

    SINGULARITY_BUILDER = SingularityBuilder(CONF_FOLDER)
    SINGULARITY_BUILDER.describe()
