# -*- coding: utf-8 -*-
"""AnacondaBuilder is a builder that builds using Anaconda.
"""
import sys
import re
import os
import shutil
from glob import glob
import json
import copy
import requests
import sh

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule
from buildrules.common.utils import (load_yaml, write_yaml, makedirs,
    copy_file, write_template, calculate_file_checksum,
    calculate_dict_checksum)

class AnacondaBuilder(Builder):
    """AnacondaBuilder extends Builder and creates build
    rules for Anaconda build.
    """

    BUILDER_NAME = 'Anaconda'
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
                        'remove_after_update': {'type': 'boolean'},
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
        """ This function returns proper values of builder paths. All
        instances of $conda are removed from configuration file and replaced
        with the default path.

        Args:
            path_name (str): Name of the required path.
        Returns:
            str: The required path.
        """
        path_config = {
            'install_path': '$conda/opt/conda/software',
            'module_path': '$conda/opt/conda/modules',
            'source_cache': '$conda/var/conda/cache',
            'tmpdir': '/tmp',
        }
        path_config.update(self._confreader['config']['config'])
        return re.sub('\$conda', self._conda_path, path_config[path_name])

    def _get_directory_creation_rules(self):
        """ This function returns builds rules that create required directories.

        Returns:
            list: List of build rules.
        """
        rules = []

        rules.extend([
            LoggingRule('Creating installer cache directory: %s' % self._installer_cache),
            PythonRule(makedirs, [self._installer_cache, 0o755]),
            LoggingRule('Creating package cache directory: %s' % self._pkg_cache),
            PythonRule(makedirs, [self._pkg_cache, 0o755]),
            LoggingRule('Creating temporary directory: %s' % self._tmpdir),
            PythonRule(makedirs, [self._tmpdir]),
            LoggingRule('Creating installation directory: %s' % self._install_path),
            PythonRule(makedirs, [self._install_path, 0o755]),
            LoggingRule('Creating module directory: %s' % self._module_path),
            PythonRule(makedirs, [self._module_path, 0o755]),
        ])

        return rules

    def _create_environment_config(self, environment_dict):
        """ This function creates an Anaconda environment configuration
        based on a environment dictionary read from a configuration
        file.

        Args:
            environment_dict (dict): Environment dictionary that will be
                used to create the environment config.
        Returns:
            dict: Environment configuration.
        """
        default_config = {
            'miniconda': True,
            'python_version': 3,
            'installer_version': 'latest',
            'pip_packages': [],
            'conda_packages': [],
        }

        environment_config = copy.deepcopy(default_config)
        environment_config.update(environment_dict)
        environment_config['environment_name'] = '{name}/{version}'.format(**environment_config)

        # Calculate checksum based on the current state of the environment_config
        environment_config['checksum'] = calculate_dict_checksum(environment_config)
        environment_config['checksum_small'] = environment_config['checksum'][:8]

        return environment_config

    def _get_installer_path(self, environment_config):
        """ This function returns a path to an installer file based on
        an environment_config.

        Args:
            environment_config (dict): Anaconda environment config.
        Returns:
            str: Path to installer file.
        """

        if environment_config['miniconda']:
            installer_fmt = "Miniconda{python_version}-{installer_version}-Linux-x86_64.sh"
        else:
            installer_fmt = "Anaconda{python_version}-{installer_version}-Linux-x86_64.sh"

        installer = os.path.join(self._installer_cache, installer_fmt.format(**environment_config))

        return installer

    def _download_installer(self, environment_config):
        """ This function downloads an installer and calculates its checksum
        based on an environment_config.

        Args:
            environment_config (dict): Anaconda environment config.
        """

        cached_installer = self._get_installer_path(environment_config)
        installer = os.path.basename(cached_installer)

        if environment_config['miniconda']:
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
            calculated_checksum = calculate_file_checksum(cached_installer)
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

    def _get_install_path(self, environment_config):
        """ This function returns the software installation path based on an
        environment_config.

        Args:
            environment_config (dict): Anaconda environment config.
        Returns:
            str: Installation path.
        """

        install_path = os.path.join(
            self._install_path,
            environment_config['name'],
            environment_config['version'],
            environment_config['checksum_small'])
        return install_path

    def _get_module_path(self, environment_config):
        """ This function returns a path to the module folder based on an
        an environment_config.

        Args:
            environment_config (dict): Anaconda environment config.
        Returns:
            str: Path to module folder.
        """

        module_path = os.path.join(
            self._module_path,
            environment_config['name'])
        return module_path

    @classmethod
    def _get_environment_file_path(cls, conda_path):
        """ This function returns a path to an environment file that contains
        installed packages based on an Anaconda environment installation path.

        Args:
            conda_path (str): Anaconda environment installation path.
        Returns:
            str: Path to environment file.
        """

        return os.path.join(conda_path, 'environment.yml')

    @classmethod
    def _write_modulefile(cls, environment_config, module_path, install_path):
        """ This function writes a modulefile that points to Anaconda
        environment constructed from environment_config and installed in
        install_path into a directory given by module_path.

        Args:
            environment_config (dict): Anaconda environment config.
            module_path (str): Directory for the modulefile.
            install_path (str): Installation path of the environment.
        """

        moduleconfig = {
            'install_path': install_path,
        }

        moduleconfig.update(environment_config)

        template = """
            -- -*- lua -*-
            --
            -- Module file created by Anaconda builder
            --

            whatis([[Name : {{ name }}]])
            whatis([[Version : {{ version }}]])
            help([[This is an automatically created Anaconda installation.]])

            prepend_path("PATH", "{{ install_path }}/bin")
        """

        modulename = '{version!s}.lua'.format(**moduleconfig)

        modulefile = os.path.join(module_path, modulename)

        write_template(modulefile, moduleconfig, template=template, chmod=0o644)

    def _remove_environment(self, install_path):
        """ This function removes installation situated in install_path.

        Args:
            install_path (str): Path to the environment.
        """

        if os.path.isdir(install_path):
            self._logger.info((
                "Cleaning previous failed installation: %s"), install_path)
            shutil.rmtree(install_path)

    def _clean_modules(self):
        """ This function removes all existing modulefiles.
        """

        if os.path.isdir(self._module_path):
            modulefiles = glob(
                os.path.join(self._module_path, '*', '*.lua')
            )
            for modulefile in modulefiles:
                os.remove(modulefile)

    def _get_installed_environments(self):
        """ This function returns a dictionary that contains information on
        already installed environments.

        Returns:
            dict: Dictionary of previously installed environments.
        """

        installed_dict = {
            'environments': {}
        }
        if os.path.isfile(self._installed_file):
            installed_dict = load_yaml(self._installed_file)
        return installed_dict

    def _update_installed_environments(self, environment_name, environment_config):
        """ This function updates the file that contains information on the
        previously installed environments.

        Args:
            environment_name (str): Name of the environment.
            environment_config (dict): Anaconda environment config.
        """

        installed_dict = self._get_installed_environments()
        installed_dict['environments'][environment_name] = environment_config
        write_yaml(self._installed_file, installed_dict)

    def _update_condarc(self, conda_path, condarc):
        """ This function updates the .condarc-file located in conda_path
        based on condarc.

        Args:
            conda_path (str): Path to Anaconda installation.
            condarc (dict): Dictionary of condarc contents.
        """

        condarc_defaults = {
            'pkgs_dirs': [self._pkg_cache],
            'always_yes': True,
            'auto_update_conda': True,
        }
        condarc.update(condarc_defaults)
        condarc_file = os.path.join(conda_path, '.condarc')
        write_yaml(condarc_file, condarc)

    def _export_conda_environment(self, conda_path):
        """ This function exports an environment.yml from an Anaconda
        environment installed in conda_path.

        Args:
            conda_path (str): Anaconda installation path.
        """

        conda_cmd = sh.Command(os.path.join(conda_path, 'bin', 'conda'))
        conda_env_json = conda_cmd('env', 'export', '-n', 'base', '--json')
        conda_env_json = conda_env_json.stdout.decode('utf-8')
        # Remove conda packages as they break updating the installation
        conda_env_json = re.sub('^.*conda.*=.*=.*\n', '',
                                conda_env_json, flags=re.MULTILINE)
        conda_env = json.loads(conda_env_json)
        write_yaml(self._get_environment_file_path(conda_path), conda_env)

    @classmethod
    def _verify_condarc(cls, conda_path):
        """ This function verifies that the Anaconda installed in
        conda_path only utilizes the .condarc-file located in its
        installation directory.

        Args:
            conda_path (str): Anaconda installation path.
        Raises:
            Exception: Raises exception when other configuration files
                are present.
        """

        conda_cmd = sh.Command(os.path.join(conda_path, 'bin', 'conda'))
        config_json = conda_cmd('info', '--json').stdout.decode('utf-8')
        config = json.loads(config_json)
        conda_rc = os.path.join(conda_path, 'condarc')
        if config['config_files']:
            if len(config['config_files']) > 1:
                raise Exception(
                    ('Too many configuration files: '
                     '{0}').format(config['config_files']))
            if config['config_files'][0] != conda_rc:
                raise Exception(
                    ('Configuration file is not from the '
                     'installation root: {0}'.format(config['config_files'])))

    def _get_environment_install_rules(self):
        """ This function returns build rules that install Anaconda environments.

        Returns:
            list: List of build rules that install Anaconda environments.
        """

        rules = []

        # Obtain already installed environments
        installed_environments = self._get_installed_environments()['environments']

        remove_after_update = self._confreader['config']['config'].get(
                'remove_after_update',
                False)

        # Only use system paths during installations
        env_path = list(filter(
            lambda x: re.search('^/(usr|bin|sbin)', x),
            os.getenv('PATH').split(':')))
        for environment in self._confreader['build_config']['environments']:

            environment_config = self._create_environment_config(environment)

            environment_name = environment_config['environment_name']
            pip_packages = environment_config.pop('pip_packages', [])
            conda_packages = environment_config.pop('conda_packages', [])
            condarc = environment_config.pop('condarc', {})

            installer = self._get_installer_path(environment_config)
            install_path = self._get_install_path(environment_config)

            conda_install_cmd = ['conda', 'install', '--yes', '-n', 'base']
            pip_install_cmd = ['pip', 'install', '--cache-dir', self._pip_cache]

            environment_config['install_path'] = install_path
            environment_config['environment_file'] = self._get_environment_file_path(install_path)

            # Add new installation path to PATH
            conda_env = {
                'PATH': ':'.join([os.path.join(install_path, 'bin')] + env_path)
            }

            skip_install = False
            update_install = False

            # Check if same kind of an environment is already installed
            installed_checksum = installed_environments.get(
                environment_name, {}).get('checksum', '')

            if not installed_checksum:
                install_msg = ("Environment {environment_name} "
                               "not installed. Starting installation.")
            elif installed_checksum != environment_config['checksum']:
                previous_environment = installed_environments[environment_name]['environment_file']
                previous_install_path = installed_environments[environment_name]['install_path']
                install_msg = ("Environment {environment_name} installed "
                               "but marked for update.")
                update_install = True
            else:
                install_msg = ("Environment {environment_name} is already installed. "
                               "Skipping installation.")
                skip_install = True

            rules.append(LoggingRule(install_msg.format(**environment_config)))

            if skip_install:
                continue

            # Install base environment
            rules.extend([
                PythonRule(self._remove_environment, [install_path]),
                PythonRule(self._download_installer, [environment_config]),
                PythonRule(
                    makedirs,
                    [install_path, 0o755],
                ),
                SubprocessRule(
                    ['bash', installer, '-f', '-b', '-p', install_path],
                    shell=True
                ),
            ])

            # Create condarc for the installed environment
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

            # During update, install old packages using environment.yml
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

            # Install packages using conda
            if conda_packages:
                rules.extend([
                    LoggingRule('Installing conda packages.'),
                    SubprocessRule(
                        conda_install_cmd + conda_packages,
                        env=conda_env,
                        shell=True),
                ])

            # Install packages using pip
            if pip_packages:
                rules.extend([
                    LoggingRule('Installing pip packages.'),
                    SubprocessRule(
                        pip_install_cmd + pip_packages,
                        env=conda_env,
                        shell=True),
                ])

            # Create environment.yml
            rules.extend([
                LoggingRule('Creating environment.yml from newly built environment.'),
                PythonRule(
                    self._export_conda_environment,
                    [install_path])
            ])

            # Add newly created environment to installed environments
            rules.append(
                PythonRule(
                    self._update_installed_environments,
                    [environment_config['environment_name'], environment_config]))

            if update_install and remove_after_update:
                rules.extend([
                    LoggingRule(('Removing old environment from '
                                 '{0}').format(previous_install_path)),
                    PythonRule(self._remove_environment, [previous_install_path])])

        return rules

    def _get_modulefile_install_rules(self):
        """ This function creates build rules that install modulefiles.

        Returns:
            list: List of build rules.
        """

        rules = []

        # Clean up modulefiles
        rules.extend([
            LoggingRule("Cleaning previous modulefiles."),
            PythonRule(self._clean_modules),
            LoggingRule('Writing modulefiles.'),
        ])

        # Create new modulefiles
        for environment in self._confreader['build_config']['environments']:

            environment_config = self._create_environment_config(environment)

            install_path = self._get_install_path(environment_config)
            module_path = self._get_module_path(environment_config)

            rules.extend([
                PythonRule(
                    makedirs,
                    [module_path, 0o755]),
                PythonRule(
                    self._write_modulefile,
                    [environment_config, module_path, install_path])
            ])

        return rules

    def _get_rules(self):
        """_get_rules provides build rules for the builder.

        Anaconda build consists of the following steps:

        1. Create directories for software, modules and temporary files.
        2. Install environments.
        3. Install modulefiles.

        Returns:
            list: List of build rules.
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
