# -*- coding: utf-8 -*-
"""AnacondaBuilder is a builder that builds using anaconda.
"""
import sys
import re
import os
import shutil
import logging
from glob import glob
import json
import copy
import requests
import sh
import yaml

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule

class YAMLDumper(yaml.SafeDumper):

    def increase_indent(self, flow=False, indentless=False):
        return super(YAMLDumper, self).increase_indent(flow, False)

def remove_tabs(string):
    return re.sub('\t', '  ', string)

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
                        'module_path': {'type': 'string'},
                        'source_cache': {'type': 'string'},
                        'tmpdir': {'type': 'string'},
                    },
                },
            },
        }, {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Package configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                'installer_checksums': {
                    'type': 'object',
                    'default': {},
                },
                'environments': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'version': {'type': 'string'},
                            'miniconda': {'type': 'boolean'},
                            'installer_version': {'type': 'string'},
                            'python_version': {
                                'type': 'integer',
                                'minimum': 2,
                                'maximum': 3,
                            },
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
                            'condarc': {
                                'default' : {},
                                'type': 'object',
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
        source_cache = self._get_path('source_cache')
        self._installer_cache = os.path.join(source_cache, 'installers')
        self._pkg_cache = os.path.join(source_cache, 'pkgs')
        self._pip_cache = os.path.join(source_cache, 'pip')
        self._tmpdir = self._get_path('tmpdir')
        self._install_path = self._get_path('install_path')
        self._module_path = self._get_path('module_path')
        self._installed_file = os.path.join(self._install_path, 'installed_environments.yml')

    def _get_path(self, path_name):
        path_config = {
            'install_path': '$conda/opt/conda/software',
            'module_path': '$conda/opt/conda/modules',
            'source_cache': '$conda/var/conda/cache',
            'tmpdir': '/tmp',
        }
        path_config.update(self._confreader['config']['config'])
        return re.sub('\$conda', self._conda_path, path_config[path_name])

    def _get_directory_creation_rules(self):
        rules = []

        rules.extend([
            LoggingRule('Creating installer cache directory: %s' % self._installer_cache),
            PythonRule(self._makedirs, [self._installer_cache, 0o755]),
            LoggingRule('Creating package cache directory: %s' % self._pkg_cache),
            PythonRule(self._makedirs, [self._pkg_cache, 0o755]),
            LoggingRule('Creating temporary directory: %s' % self._tmpdir),
            PythonRule(self._makedirs, [self._tmpdir]),
            LoggingRule('Creating installation directory: %s' % self._install_path),
            PythonRule(self._makedirs, [self._install_path, 0o755]),
            LoggingRule('Creating module directory: %s' % self._module_path),
            PythonRule(self._makedirs, [self._module_path, 0o755]),
        ])

        return rules

    def _create_environment_config(self, environment_dict):
        default_config = {
            'miniconda': True,
            'python_version': 3,
            'installer_version': 'latest',
            'pip_packages': [],
            'conda_packages': [],
        }

        config = copy.deepcopy(default_config)
        config.update(environment_dict)
        config['environment_name'] = '{name}/{version}'.format(**config)

        config['checksum'] = self._calculate_dict_checksum(config)
        config['checksum_small'] = config['checksum'][:8]

        return config

    def _get_installer_path(self, install_config):

        if install_config['miniconda']:
            installer_fmt = "Miniconda{python_version}-{installer_version}-Linux-x86_64.sh"
        else:
            installer_fmt = "Anaconda{python_version}-{installer_version}-Linux-x86_64.sh"

        installer = os.path.join(self._installer_cache, installer_fmt.format(**install_config))

        return installer

    def _download_installer(self, install_config):

        cached_installer = self._get_installer_path(install_config)
        installer = os.path.basename(cached_installer)

        if install_config['miniconda']:
            installer_url = "https://repo.anaconda.com/miniconda/{0}".format(installer)
        else:
            installer_url = "https://repo.anaconda.com/archive/{0}".format(installer)

        if not os.path.isfile(cached_installer):
            self._logger.info((
                "Installer '%s' was not found in the cache directory. "
                "Downloading it."), installer)
            download_request = requests.get(installer_url)
            with open(cached_installer, 'wb') as installer_file:
                installer_file.write(download_request.content)

        checksum = self._confreader['build_config'].get(
            'installer_checksums', {}).get(installer, '')
        if checksum:
            self._logger.info(
                "Calculating checksum for installer '%s'", installer)
            calculated_checksum = self._calculate_file_checksum(cached_installer)
            if calculated_checksum != checksum:
                self._logger.error(
                    ("The checksum for installer file '%s' "
                     "does not match the expected value:\n"
                     "Expected:   %s\n"
                     "Calculated: %s"),
                    installer,
                    checksum,
                    calculated_checksum)
                raise Exception('Invalid checksum for installer')

    def _get_install_path(self, config):
        install_path = os.path.join(
            self._install_path,
            config['name'],
            config['version'],
            config['checksum_small'])
        return install_path

    def _get_module_path(self, config):
        module_path = os.path.join(
            self._module_path,
            config['name'])
        return module_path

    def _get_environment_file_path(self, conda_path):
        return os.path.join(conda_path, 'environment.yml')

    def _write_modulefile(self, config, module_path, install_path):

        moduleconfig = {
            'install_path':install_path,
        }

        moduleconfig.update(config)

        template = ("-- -*- lua -*-\n"
                    "--\n"
                    "-- Module file created by anaconda builder\n"
                    "--\n\n"
                    "whatis([[Name : {name!s}]])\n"
                    "whatis([[Version : {version!s}]])\n"
                    "help([[This is an automatically created \n"
                    "anaconda installation.]])\n\n"
                    'prepend_path("PATH", "{install_path!s}/bin")\n')

        module = template.format(**moduleconfig)
        modulename = '{version!s}.lua'.format(**moduleconfig)

        modulepath = os.path.join(module_path, modulename)

        with open(modulepath, 'w') as modulefile:
            modulefile.write(module)

        os.chmod(modulepath, 0o644)

    def _clean_failed(self, install_path):
        if os.path.isdir(install_path):
            self._logger.info((
                "Cleaning previous failed installation: %s"), install_path)
            shutil.rmtree(install_path)

    def _clean_modules(self):
        if os.path.isdir(self._module_path):
            modulefiles = glob(
                os.path.join(self._module_path, '*', '*.lua')
            )
            for modulefile in modulefiles:
                os.remove(modulefile)

    def _get_installed_environments(self):
        installed_dict = {
            'environments': {}
        }
        if os.path.isfile(self._installed_file):
            with open(self._installed_file, 'r') as installed_file:
                installed_dict = yaml.load(installed_file, Loader=yaml.SafeLoader)
        return installed_dict

    def _update_installed_environments(self, environment_name, installation_config):
        installed_dict = self._get_installed_environments()
        installed_dict['environments'][environment_name] = installation_config
        with open(self._installed_file, 'w') as installed_file:
            installed_file.write(
                remove_tabs(
                    yaml.dump(
                        installed_dict,
                        default_flow_style=False,
                        Dumper=YAMLDumper
                )))

    def _update_condarc(self, conda_path, condarc):
        condarc_defaults = {
            'pkgs_dirs': [self._pkg_cache],
            'always_yes': True,
            'auto_update_conda': True,
        }
        condarc.update(condarc_defaults)
        with open(os.path.join(conda_path, '.condarc'), 'w') as condarc_file:
            condarc_file.write(
                remove_tabs(
                    yaml.dump(
                        condarc,
                        default_flow_style=False,
                        Dumper=YAMLDumper
                )))

    def _export_conda_environment(self, conda_path):
        conda_cmd = sh.Command(os.path.join(conda_path, 'bin', 'conda'))
        conda_env_json = conda_cmd('env', 'export', '-n', 'base', '--json')
        conda_env_json = conda_env_json.stdout.decode('utf-8')
        conda_env = json.loads(conda_env_json)
        with open(self._get_environment_file_path(conda_path), 'w') as conda_env_file:
            conda_env_file.write(
                remove_tabs(
                    yaml.dump(
                        conda_env,
                        default_flow_style=False,
                        Dumper=YAMLDumper
                )))

    @classmethod
    def _verify_condarc(cls, conda_path):
        conda_cmd = sh.Command(os.path.join(conda_path, 'bin', 'conda'))
        config_json = conda_cmd('info', '--json').stdout.decode('utf-8')
        config = json.loads(config_json)
        conda_rc = os.path.join(conda_path, 'condarc')
        if config['config_files']:
            if len(config['config_files']) > 1:
                raise Exception(
                    ('Too many configuration files: '
                     '{0}').format(config['config_files']))
            elif config['config_files'][0] != conda_rc:
                raise Exception(
                    ('Configuration file is not from the '
                     'installation root: {0}'.format(config['config_files'])))

    def _get_environment_install_rules(self):
        rules = []

        installed_environments = self._get_installed_environments()['environments']

        env_path = list(filter(
            lambda x: re.search('^/(usr|bin|sbin)', x),
            os.getenv('PATH').split(':')))

        for environment in self._confreader['build_config']['environments']:

            config = self._create_environment_config(environment)

            environment_name = config['environment_name']
            pip_packages = config.pop('pip_packages', [])
            conda_packages = config.pop('conda_packages', [])
            condarc = config.pop('condarc', {})

            installer = self._get_installer_path(config)
            install_path = self._get_install_path(config)
            module_path = self._get_module_path(config)

            conda_install_cmd = ['conda', 'install', '--yes', '-n', 'base']
            pip_install_cmd = ['pip', 'install', '--cache-dir', self._pip_cache]

            config['environment_file'] = self._get_environment_file_path(install_path)

            conda_env = {
                'PATH': ':'.join([os.path.join(install_path, 'bin')] + env_path)
            }

            config['install_environment'] = conda_env

            skip_install = False
            update_install = False

            installed_checksum = installed_environments.get(
                environment_name, {}).get('checksum', '')

            if not installed_checksum:
                install_msg = ("Environment {environment_name} "
                               "not installed. Starting installation.")
            elif installed_checksum != config['checksum']:
                previous_environment = installed_environments.get(
                    environment_name, {}).get('environment_file', None)
                install_msg = ("Environment {environment_name} installed "
                               "but marked for update.")
                update_install = True
            else:
                install_msg = ("Environment {environment_name} is already installed. "
                               "Skipping installation.")
                skip_install = True

            rules.append(LoggingRule(install_msg.format(**config)))

            if skip_install:
                continue


            rules.extend([
                PythonRule(self._clean_failed, [install_path]),
                PythonRule(self._download_installer, [config]),
                PythonRule(
                    self._makedirs,
                    [install_path, 0o755],
                ),
                SubprocessRule(
                    ['bash', installer, '-f', '-b', '-p', install_path],
                    shell=True
                ),
            ])

            rules.extend([
                LoggingRule('Verifying that only the environment condarc is utilized.'),
                PythonRule(
                    self._verify_condarc,
                    [install_path]
                ),
                LoggingRule('Creating condarc for environment.'),
                PythonRule(
                    self._update_condarc,
                    [install_path, condarc],
                ),
            ])

            if update_install:
                rules.extend([
                    SubprocessRule(
                        ['conda', 'env', 'update',
                        '--file', previous_environment,
                        '--prefix', install_path],
                        env=conda_env,
                        shell=True)])

                conda_install_cmd.append('--freeze-installed')
                pip_install_cmd.extend([
                    '--upgrade', '--upgrade-strategy', 'only-if-needed'])

            if conda_packages:
                rules.extend([
                    LoggingRule('Installing conda packages.'),
                    SubprocessRule(
                        conda_install_cmd + conda_packages,
                        env=conda_env,
                        shell=True),
                ])

            if pip_packages:
                rules.extend([
                    LoggingRule('Installing pip packages.'),
                    SubprocessRule(
                        pip_install_cmd + pip_packages,
                        env=conda_env,
                        shell=True),
                ])

            rules.extend([
                LoggingRule('Creating environment.yml from newly built environment.'),
                PythonRule(
                    self._export_conda_environment,
                    [install_path])
            ])

            rules.append(
                PythonRule(
                    self._update_installed_environments,
                    [config['environment_name'], config]))

        return rules

    def _get_modulefile_install_rules(self):
        rules = []

        rules.extend([
            LoggingRule("Cleaning previous modulefiles."),
            PythonRule(self._clean_modules),
            LoggingRule('Writing modulefiles.'),
        ])

        for environment in self._confreader['build_config']['environments']:

            config = self._create_environment_config(environment)

            install_path = self._get_install_path(config)
            module_path = self._get_module_path(config)

            rules.extend([
                PythonRule(
                    self._makedirs,
                    [module_path, 0o755]),
                PythonRule(
                    self._write_modulefile,
                    [config, module_path, install_path])
            ])

        return rules

    def _get_rules(self):
        """_get_rules provides build rules for the builder.

        Anaconda build consists of the following steps:

        """

        rules = (
            self._get_directory_creation_rules() +
            self._get_environment_install_rules() +
            self._get_modulefile_install_rules()
        )
        return rules

if __name__ == "__main__":

    CONF_FOLDER = sys.argv[1]

    ANACONDA_BUILDER = AnacondaBuilder(CONF_FOLDER)
    ANACONDA_BUILDER.describe()
