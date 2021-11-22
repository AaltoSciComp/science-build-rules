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
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule, RuleError
from buildrules.common.utils import (load_yaml, write_yaml, makedirs,
                                     copy_file, write_template,
                                     calculate_file_checksum,
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
                        'conda_pack_path': {'type': 'string'},
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
                'collections': {
                    'type': 'object',
                    'additionalProperties': False,
                    'patternProperties': {
                        '.*': {
                            'type': 'object',
                            'additionalProperties': False,
                            'patternProperties': {
                                ('(conda|pip)'
                                 '_packages'): {
                                     'type': 'array',
                                     'default': [],
                                     'items': {'type': 'string'}
                                },
                            },
                        },
                    },
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
                            'mamba': {'type': 'boolean'},
                            'conda_pack': {'type': 'boolean'},
                            'installer_version': {'type': 'string'},
                            'freeze': {'type': 'boolean'},
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
                            'condarc_install': {
                                'default' : {},
                                'type': 'object',
                            },
                            'collections': {
                                'type': 'array',
                                'items': {'type': 'string'}
                            },
                            'extra_module_variables': {
                                'type': 'object',
                                'additionalProperties': False,
                                'patternProperties': {
                                    '(setenv|prepend_path|append_path)': {
                                        'type': 'object',
                                        'patternProperties': {
                                            '.*': {'type': 'string'},
                                        },
                                    },
                                },
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
        self.remove_after_update = self._confreader['config']['config'].get(
            'remove_after_update',
            False)
        self._collections = self._confreader['build_config'].get(
            'collections', {})


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
            'mamba': True,
            'conda_pack': False,
            'python_version': 3,
            'installer_version': 'latest',
            'pip_packages': [],
            'conda_packages': [],
            'extra_module_variables': {},
        }

        environment_config = copy.deepcopy(default_config)
        environment_config.update(environment_dict)
        environment_config['environment_name'] = '{name}/{version}'.format(**environment_config)

        # Combining packages from all of the different collections
        for collection in environment_config.pop('collections', []):
            conda_packages = self._collections[collection].get('conda_packages', [])
            pip_packages = self._collections[collection].get('pip_packages', [])

            environment_config['conda_packages'].extend(conda_packages)
            environment_config['pip_packages'].extend(pip_packages)

        environment_config['conda_packages'].sort()
        environment_config['pip_packages'].sort()

        if environment_config['mamba']:
            environment_config['conda_cmd'] = 'mamba'
        else:
            environment_config['conda_cmd'] = 'conda'

        # Remove freeze temporarily from configuration as that should not be included in checksum calculation
        freeze = environment_config.pop('freeze', False)
        conda_pack = environment_config.pop('conda_pack', False) 

        # Calculate checksum based on the current state of the environment_config
        environment_config['checksum'] = calculate_dict_checksum(environment_config)
        environment_config['checksum_small'] = environment_config['checksum'][:8]

        environment_config['freeze'] = freeze
        environment_config['conda_pack'] = conda_pack 

        return environment_config

    def _get_installer_path(self, environment_config, update_installer=False):
        """ This function returns a path to an installer file based on
        an environment_config.

        Args:
            environment_config (dict): Anaconda environment config.
            update_installer (boolean): Give installer for updating an environment.
        Returns:
            str: Path to installer file.
        """

        if update_installer:
            installer_fmt = "Miniconda{python_version}-latest-Linux-x86_64.sh"
        elif environment_config['miniconda']:
            installer_fmt = "Miniconda{python_version}-{installer_version}-Linux-x86_64.sh"
        else:
            installer_fmt = "Anaconda{python_version}-{installer_version}-Linux-x86_64.sh"

        installer = os.path.join(self._installer_cache, installer_fmt.format(**environment_config))

        return installer

    def _download_installer(self, installer_path):
        """ This function downloads an installer and calculates its checksum
        based on an installer path.

        Args:
            installer_path (str): Path for the installer.
        """

        installer = os.path.basename(installer_path)

        if 'Miniconda' in installer_path:
            installer_url = "https://repo.anaconda.com/miniconda/{0}".format(installer)
        else:
            installer_url = "https://repo.anaconda.com/archive/{0}".format(installer)

        if not os.path.isfile(installer_path):
            self._logger.info((
                "Installer '%s' was not found in the cache directory. "
                "Downloading it."), installer)
            download_request = requests.get(installer_url)
            with open(installer_path, 'wb') as installer_file:
                installer_file.write(download_request.content)

        checksum = self._confreader['build_config'].get(
            'installer_checksums', {}).get(installer, '')
        if checksum:
            self._logger.info(
                "Calculating checksum for installer '%s'", installer)
            calculated_checksum = calculate_file_checksum(installer_path)
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
    def _write_modulefile(cls, name, version, install_path, module_path, extra_module_variables):
        """ This function writes a modulefile that points to Anaconda
        environment installed in install_path and whose name is name/version
        into a directory given by module_path.

        Args:
            name (str): Name of the Anaconda module.
            version (str): Version of the Anaconda module.
            install_path (str): Installation path of the environment.
            module_path (str): Directory for the modulefile.
            extra_module_variables (dict): Additional environment variables to add to the modulefile.
        """

        # Replace instances of $prefix from extra module variables
        modulevars = copy.deepcopy(extra_module_variables)

        def replace_prefix(variable_value):
            return variable_value.replace('$prefix', install_path)

        for env_function in modulevars:
            for variable in modulevars[env_function]:
                modulevars[env_function][variable] = replace_prefix(modulevars[env_function][variable])


        moduleconfig = {
            'name' : name,
            'version': version,
            'install_path': install_path,
            'extra_module_variables': modulevars,
        }

        template = """
            -- -*- lua -*-
            --
            -- Module file created by Anaconda builder
            --

            whatis([[Name : {{ name }}]])
            whatis([[Version : {{ version }}]])
            help([[This is an automatically created Anaconda installation.]])

            prepend_path("PATH", "{{ install_path }}/bin")
            setenv("CONDA_PREFIX", "{{ install_path }}")
            {%- for env_function, variables in extra_module_variables.items() %}
            {%- for variable_name, variable_value in variables.items() %}
            {{ env_function }}("{{ variable_name }}", "{{ variable_value }}")
            {%- endfor %}
            {%- endfor %}
        """

        makedirs(module_path, 0o755)

        modulefile = os.path.join(module_path, '%s.lua' % version)

        if os.path.exists(modulefile):
            raise RuleError('Modulefile %s already exists' % modulefile)

        write_template(modulefile, moduleconfig, template=template, chmod=0o644)

    def _remove_environment(self, install_path):
        """ This function removes installation situated in install_path.

        Args:
            install_path (str): Path to the environment.
        """

        if os.path.isdir(install_path):
            self._logger.info((
                "Cleaning previous failed installation: %s"), install_path)
            sh.rm('-r', '-f', install_path)

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
        # Remove old environments that have been removed from the installation path
        removed_environments = []
        for environment in installed_dict['environments']:
            if not os.path.isdir(installed_dict['environments'][environment]['install_path']):
                removed_environments.append(environment)
        for environment in removed_environments:
            del installed_dict['environments'][environment]
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

    def _update_condarc(self, conda_path, condarc, condarc_install, install_time=True):
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

        condarc_complete = {}
        if install_time:
            condarc_complete.update(condarc_defaults)
            condarc_complete.update(condarc_install)
        condarc_complete.update(condarc)
        condarc_file = os.path.join(conda_path, '.condarc')
        write_yaml(condarc_file, condarc_complete)


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


    def _conda_pack_environment(self, conda_path, pack_path, name, version, checksum):
        """ This function exports an conda-pack from an Anaconda
        environment installed in conda_path.

        Args:
            conda_path (str): Anaconda installation path.
            pack_path (str): Path for the conda-packs.
            name (str): Name of the environment
            version (str): Version of the environment
            checksum (str): Checksum for the environment
        """

        conda_cmd = sh.Command(os.path.join(conda_path, 'bin', 'conda'))

        output_pack = os.path.join(pack_path, '{0}_{1}_{2}.tar.gz'.format(name, version, checksum))

        if not os.path.isfile(output_pack):
            conda_pack_output = conda_cmd('pack', '-p', conda_path, '-o', output_pack)


    def _sanitize_environment_file(self, old_environment_file, new_environment_file):
        """ This function sanitizes environment.yml created by previous
        installation by removing pip packages from dependencies.

        Args:
            install_path (str): New installation path where environment.yml
                will be written.
            environment_file (str): Previous environment file that will be
                sanitized.
        """
        conda_env = load_yaml(old_environment_file)
        dependencies = [
            dependency for dependency in conda_env.pop('dependencies')
            if not isinstance(dependency, dict)
        ]
        conda_env['dependencies'] = dependencies
        write_yaml(new_environment_file, conda_env)

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


    def _install_package_tools(self, conda_path, install_mamba, install_conda_pack):
        """ This installs mamba package manager if installation
        uses mamba and conda-pack if installation wants to use conda-pack
        for packaging.

        Args:
            conda_path (str): Anaconda installation path.
            install_mamba (bool): Should mamba be installed.
            install_conda_pack (bool): Should conda-pack be installed.
        """

        conda_cmd = sh.Command(os.path.join(conda_path, 'bin', 'conda'))
        if install_mamba:
            conda_cmd('install', '--yes',
                     '--freeze-installed',
                     '-c', 'conda-forge',
                      '-n', 'base',
                      'mamba')
        if install_conda_pack:
            conda_cmd('install', '--yes',
                     '--freeze-installed',
                     '-c', 'conda-forge',
                      '-n', 'base',
                      'conda-pack')


    def _get_environment_install_rules(self):
        """ This function returns build rules that install Anaconda environments.

        Returns:
            list: List of build rules that install Anaconda environments.
        """

        rules = []

        # Obtain already installed environments
        installed_environments = self._get_installed_environments()['environments']

        # Only use system paths during installations
        env_path = list(filter(
            lambda x: re.search('^/(usr|bin|sbin)', x),
            os.getenv('PATH').split(':')))

        for environment in self._confreader['build_config']['environments']:

            environment_config = self._create_environment_config(environment)

            environment_name = environment_config['environment_name']
            pip_packages = environment_config.get('pip_packages', [])
            conda_packages = environment_config.get('conda_packages', [])
            condarc = environment_config.get('condarc', {})
            condarc_install = environment_config.get('condarc_install', {})
            extra_module_variables = environment_config.get('extra_module_variables', {})

            conda_install_cmd = [environment_config['conda_cmd'], 'install', '--yes', '-n', 'base']
            pip_install_cmd = ['pip', 'install', '--cache-dir', self._pip_cache]

            skip_install = False
            update_install = False
            freeze = environment_config.get('freeze', False)

            install_path = self._get_install_path(environment_config)
            module_path = self._get_module_path(environment_config)

            # Check if same kind of an environment is already installed
            installed_checksum = installed_environments.get(
                environment_name, {}).get('checksum', '')

            if not installed_checksum:
                install_msg = ("Environment {environment_name} "
                               "not installed. Starting installation.")
            elif installed_checksum != environment_config['checksum'] and not freeze:
                previous_environment = installed_environments[environment_name]['environment_file']
                previous_install_path = installed_environments[environment_name]['install_path']
                install_msg = ("Environment {environment_name} installed "
                               "but marked for update.")
                update_install = True
            else:
                install_msg = ("Environment {environment_name} is already installed. "
                               "Skipping installation.")
                install_path = installed_environments[environment_name]['install_path']
                module_path = installed_environments[environment_name]['module_path']
                skip_install = True

            installer = self._get_installer_path(environment_config, update_installer=update_install)

            # Add new installation path to PATH
            conda_env = {
                'PATH': ':'.join([os.path.join(install_path, 'bin')] + env_path),
                'PYTHONUNBUFFERED': '1',
            }

            environment_config['install_path'] = install_path
            environment_config['module_path'] = module_path
            environment_config['environment_file'] = self._get_environment_file_path(install_path)

            rules.append(LoggingRule(install_msg.format(**environment_config)))

            if not skip_install:
                # Install base environment
                rules.extend([
                    PythonRule(self._remove_environment, [install_path]),
                    PythonRule(self._download_installer, [installer]),
                    PythonRule(
                        makedirs,
                        [install_path, 0o755],
                    ),
                    SubprocessRule(
                        ['bash', installer, '-f', '-b', '-p', install_path],
                        shell=True
                    ),
                ])

                rules.extend([
                    # Verify no external condarc is used
                    LoggingRule('Verifying that only the environment condarc is utilized.'),
                    PythonRule(
                        self._verify_condarc,
                        [install_path]
                    ),
                    # Install mamba if needed
                    LoggingRule('Installing mamba & conda-pack if needed.'),
                    PythonRule(
                        self._install_package_tools,
                        [
                            install_path,
                            environment_config['mamba'],
                            environment_config.get('conda_pack', False)
                        ],
                    ),
                    # Create condarc for the installed environment
                    LoggingRule('Creating condarc for environment.'),
                    PythonRule(
                        self._update_condarc,
                        [install_path, condarc, condarc_install],
                    ),
                ])

                # During update, install old packages using environment.yml
                if update_install:
                    rules.extend([
                        LoggingRule(
                            ('Sanitizing environment file from previous installation '
                             '"{0}" to new installation "{1}"').format(
                                 previous_environment,
                                 environment_config['environment_file'])),
                        PythonRule(
                            self._sanitize_environment_file,
                            [previous_environment, environment_config['environment_file']],
                        ),
                        LoggingRule(('Installing conda packages from previous '
                                     'installation.')),
                        SubprocessRule(
                            [environment_config['conda_cmd'], 'env', 'update',
                             '--file', environment_config['environment_file'],
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
                rules.extend([
                    LoggingRule('Updating installed_environments.yml.'),
                    PythonRule(
                        self._update_installed_environments,
                        [environment_config['environment_name'], environment_config]),
                ])

                if update_install and self.remove_after_update:
                    rules.extend([
                        LoggingRule(('Removing old environment from '
                                     '{0}').format(previous_install_path)),
                        PythonRule(self._remove_environment, [previous_install_path])])

            # Update .condarc
            rules.extend([
                LoggingRule('Creating condarc for environment: %s' % environment_name),
                PythonRule(
                    self._update_condarc,
                    [install_path, condarc, condarc_install],
                    {'install_time': False})
            ])

            # Pack the environment
            if environment_config.get('conda_pack', False):
                rules.extend([
                    LoggingRule('Creating conda-pack from the environment.'),
                    PythonRule(
                        self._conda_pack_environment,
                        [
                            install_path,
                            environment_config.get('conda_pack_path', install_path),
                            environment_config['name'],
                            environment_config['version'],
                            environment_config['checksum_small'],
                        ])
                ])

            # Create modulefile for the environment
            rules.extend([
                LoggingRule('Creating modulefile for environment: %s' % environment_name),
                PythonRule(
                    self._write_modulefile,
                    [environment_config['name'],
                     environment_config['version'],
                     install_path,
                     module_path,
                     extra_module_variables])
            ])

        return rules

    def _get_modulefile_clean_rules(self):
        """ This function creates build rules that clean up modulefiles.

        Returns:
            list: List of build rules.
        """

        rules = []

        # Clean up modulefiles
        rules.extend([
            LoggingRule("Cleaning previous modulefiles."),
            PythonRule(self._clean_modules),
        ])

        return rules

    def _get_rules(self):
        """_get_rules provides build rules for the builder.

        Anaconda build consists of the following steps:

        1. Create directories for software, modules and temporary files.
        2. Clean up modulefiles
        3. Install environments.

        Returns:
            list: List of build rules.
        """

        rules = (
            self._get_directory_creation_rules() +
            self._get_modulefile_clean_rules() +
            self._get_environment_install_rules()
        )
        return rules

if __name__ == "__main__":

    CONF_FOLDER = sys.argv[1]

    ANACONDA_BUILDER = AnacondaBuilder(CONF_FOLDER)
    ANACONDA_BUILDER.describe()
