# -*- coding: utf-8 -*-
"""SingularityBuilder is a builder that builds using singularity.
"""
import sys
import re
import os
from collections import defaultdict
import shutil
import textwrap
import logging
from glob import glob
import yaml
import copy
import requests
import sh
from jinja2.environment import Environment

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule
from buildrules.common.confreader import ConfReader

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
                    'additionalProperties': False,
                    'properties': {
                        'debug': {'type': 'boolean'},
                        'sudo': {'type': 'boolean'},
                        'fakeroot': {'type': 'boolean'},
                        'install_path': {'type': 'string'},
                        'build_stage': {'type': 'string'},
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
                'command_collections': {
                    'type': 'object',
                    'patternProperties': {
                        '.*' : {
                            'type': 'object',
                            'additionalProperties': False,
                            'patternProperties': {
                                ('(environment|files|help|labels|'
                                 'post|runscript|setup|'
                                 'startscript|test)_commands'): {
                                     'type': 'array',
                                     'default': [],
                                     'items': {'type': 'string'}
                                 },
                            },
                        },
                    },
                },
                'flag_collections': {
                    'type': 'object',
                    'patternProperties': {
                        '.*' : {
                            'type': 'array',
                            'default': [],
                            'items': {'type': 'string'}
                        },
                    },
                },
                'definitions': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'docker_user': {'type': 'string'},
                            'docker_image': {'type': 'string'},
                            'debug': {'type': 'boolean'},
                            'sudo': {'type': 'boolean'},
                            'fakeroot': {'type': 'boolean'},
                            'tags': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'flag_collections': {
                                'type': 'array',
                                'items': {'type': 'string'}
                            },
                            'command_collections': {
                                'type': 'array',
                                'items': {'type': 'string'}
                            }
                        },
                        'required': ['name', 'tags'],
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
        self._command_collections = self._confreader['build_config'].get(
            'command_collections', {})
        self._flag_collections = self._confreader['build_config'].get(
            'flag_collections', {})
        self._auths = self._get_auths()

    def _get_path(self, path_name):
        path_config = {
            'install_path': '$singularity/opt/singularity/software',
            'module_path': '$singularity/opt/singularity/modules',
            'source_cache': '$singularity/var/singularity/cache',
            'build_stage': '$singularity/var/singularity/stage',
        }
        path_config.update(self._confreader['config']['config'])
        return re.sub('\$singularity', self._singularity_path, path_config[path_name])

    def _get_auths(self):
        auth_file = os.path.expanduser(os.path.join('~', 'singularity_auths.yml'))
        auth_schema = {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Singularity auth file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                'auths': {
                    'type': 'object',
                    'default': {},
                    'patternProperties': {
                        '.*' : {
                            'type': 'object',
                            'additionalProperties': False,
                            'properties': {
                                'username': {'type': 'string'},
                                'password': {'type': 'string'},
                            },
                        },
                    },
                },
            },
        }
        auths = defaultdict(dict)
        if os.path.isfile(auth_file):
            auths = ConfReader([auth_file],[auth_schema])

        return auths

    def _get_directory_creation_rules(self):
        rules = []

        rules.extend([
            PythonRule(self._makedirs, [self._source_cache, 0o755]),
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


    def _get_build_config(self, tag, definition_dict):
        default_config = {
            'docker_user': 'library',
            'docker_image': definition_dict['name'],
            'tag': tag,
        }

        config = copy.deepcopy(default_config)
        config.update(definition_dict)

        # Setting definition name
        config['definition_name'] = '{name!s}/{tag!s}'.format(**config)

        # Combining commands from all of the different command collections
        commands = defaultdict(list)
        for command_collection in config.pop('command_collections', []):
            collection = self._command_collections[command_collection]
            for key, item in collection.items():
                keyname = re.sub('_commands', '', key)
                commands[keyname] = commands[keyname] + item
        config['commands'] = dict(commands)

        # Combining flags from all of the different flag collections
        flags = []
        for flag_collection in config.pop('flag_collections', []):
            flags = flags + self._flag_collections[flag_collection]
        config['flags'] = ' '.join(flags)

        config['checksum'] = self._calculate_dict_checksum(config)
        config['checksum_small'] = config['checksum'][:8]
        config['basename'] = '{name!s}-{tag!s}-{checksum_small!s}'.format(**config)
        config['docker_url'] = '{docker_user!s}/{docker_image!s}:{tag!s}'.format(**config)

        return config

    @classmethod
    def _get_definition_file(cls, config):

        template_base = """
            Bootstrap: docker
            From: {{ docker_url }}
            {% if registry is defined -%}
            Registry: {{ registry }}
            {% endif -%}

            {% for command_collection, commands in commands.items() -%}
            %{{ command_collection }}
            {% for command in commands -%}
                {{ command }}
            {% endfor -%}
            {% endfor -%}
        """

        template = Environment().from_string(textwrap.dedent(template_base))

        return template.render(**config)

    def _write_definition_file(self, definition_file, config):
        contents = self._get_definition_file(config)
        with open(definition_file, 'w') as def_file:
            def_file.write(contents)

    def _get_image_install_rules(self):

        rules = []

        buildenv = {
            'SINGULARITY_CACHEDIR': self._source_cache
        }

        uid = os.getuid()

        self._logger.warning(self._confreader['build_config'])
        for definition in self._confreader['build_config']['definitions']:
            self._logger.warning(definition)
            for tag in definition.pop('tags'):
                config = self._get_build_config(tag, definition)

                definition_file = os.path.join(
                    self._build_stage,
                    '{basename!s}.def'.format(**config))

                stage_image = os.path.join(
                    self._build_stage,
                    '{basename!s}.simg'.format(**config))

                rules.append(PythonRule(
                    self._write_definition_file,
                    [definition_file, config]))

                # Add --fakeroot parsing here later on

                singularity_build_cmd = ['singularity', 'build', '-F']
                chown_cmd = ['chown', '{0}:{0}'.format(uid)]

                debug = (config.get('debug', False) and
                        self._confreader['config']['config'].get('debug', False))
                sudo = (config.get('sudo', True) and
                        self._confreader['config']['config'].get('sudo', False))
                fakeroot = (config.get('fakeroot', True) and
                            self._confreader['config']['config'].get(
                                'fakeroot', False))
                if debug:
                    singularity_build_cmd.insert(1, '-d')
                if sudo:
                    singularity_build_cmd.insert(0, 'sudo')
                    chown_cmd.insert(0, 'sudo')
                if fakeroot:
                    singularity_build_cmd.append('--fakeroot')
                rules.append(
                    SubprocessRule(
                        singularity_build_cmd + [stage_image, definition_file],
                        env=buildenv,
                        shell=True))
                if sudo:
                    rules.append(
                    SubprocessRule(
                        chown_cmd + [stage_image],
                        shell=True)
                    )

        """

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
        """
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
