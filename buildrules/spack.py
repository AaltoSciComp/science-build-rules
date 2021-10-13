# -*- coding: utf-8 -*-
"""SpackBuilder is a builder that builds using spack.
"""
import sys
import re
import os
import shutil
import logging
from glob import glob
import yaml
import sh
import warnings

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule
from buildrules.common.utils import makedirs, copy_file

SPACK_ROOT=os.getenv('SPACK_ROOT', None)
if not SPACK_ROOT:
    warnings.warn('Spack environment is not activated. Spack configuration schemas are not verified correctly!')
    config_schema = {}
    modules_schema = {}
    packages_schema = {}
else:
    SPACK_LIB_PATH=os.path.join(SPACK_ROOT, 'lib/spack')
    SPACK_EXTERNAL_LIB_PATH=os.path.join(SPACK_ROOT, 'lib/spack/external')
    sys.path.append(SPACK_LIB_PATH)
    sys.path.append(SPACK_EXTERNAL_LIB_PATH)
    import spack.config
    config_schema = spack.schema.config.schema
    modules_schema = spack.schema.modules.schema
    packages_schema = spack.schema.packages.schema

class SpackBuilder(Builder):
    """SpackBuilder extends on Builder and creates buildrules for Spack build.
    """

    BUILDER_NAME = 'Spack'
    CONF_FILES = ['config.yaml', 'modules.yaml', 'packages.yaml', 'build_config.yaml']
    SCHEMAS = [
        config_schema,
        modules_schema,
        packages_schema,
        {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Package configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                'target_architecture': {
                    'type': 'object',
                    'properties': {
                        'platform': {'type': 'string'},
                        'os': {'type': 'string'},
                        'target': {'type': 'string'},
                    },
                },
                'compilers': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'version': {'type': 'string'},
                            'system_compiler': {'type': 'boolean'},
                            'licenses': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'variants': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'dependencies': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'extra_flags': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'flags': {
                                'type': 'object',
                                'properties': {
                                    'cflags': {'type': 'string'},
                                    'cxxflags': {'type': 'string'},
                                    'fflags': {'type': 'string'},
                                    'cppflags': {'type': 'string'},
                                    'ldflags': {'type': 'string'},
                                    'ldlibs': {'type': 'string'},
                                },
                            },
                        },
                        'required': ['name', 'version'],
                    },
                },
                'packages': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'version': {'type': 'string'},
                            'licenses': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'variants': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'dependencies': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'extra_flags': {
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
        self._spack_cmd = ['spack', '--config-scope', conf_folder]
        self._spack_sh = sh.spack.bake('--config-scope', conf_folder)
        self._compilers_file = os.path.expanduser('~/.spack/linux/compilers.yaml')
        super().__init__(conf_folder)

    def _get_reindex_rules(self):
        logging_rule = LoggingRule('Re-indexing installed packages.')
        reindex_rule = SubprocessRule(self._spack_cmd + ['reindex'])
        return [logging_rule, reindex_rule]

    def _get_spec_string(self, package_config):
        return ' '.join(self._get_spec_list(package_config))

    def _get_build_environment(self):
        build_env = {}
        if 'build_language' in self._confreader['config'].get('config', {}):
            build_env['LC_ALL'] = self._confreader['config']['config']['build_language']
        return build_env if len(build_env) > 0 else None

    def _get_target_architecture_flags(self, package_config):
        target_architecture = {
            'platform': 'linux',
            'os': 'None',
            'arch': 'None',
        }
        target_architecture.update(self._confreader['build_config'].get('target_architecture', {}))
        target_architecture.update(package_config.get('target_architecture', {}))
        arch_flags = ['arch={platform}-{os}-{arch}'.format(**target_architecture)]
        return arch_flags

    @classmethod
    def _get_extra_flags(cls, package_config):
        extra_flags = []
        for flag_str in package_config.get('extra_flags', []):
            extra_flags.extend(flag_str.split(' '))
        return extra_flags

    def _get_spec_list(self, package_config):
        spec_list = ['{name}@{version}'.format(**package_config)]
        spec_list.extend(package_config.get('variants', []))
        spec_list.extend(self._get_target_architecture_flags(package_config))
        spec_list.extend(package_config.get('dependencies', []))
        return spec_list

    def _remove_compilers_file(self):
        try:
            os.remove(self._compilers_file)
        except OSError:
            pass

    def _get_package_spec_rule(self, package_config):
        spec_str = self._get_spec_string(package_config)
        spec_list = self._get_spec_list(package_config)
        self._logger.debug(msg='Creating package spec rule for spec: {0}'.format(spec_str))
        return SubprocessRule(self._spack_cmd + ['spec'] + spec_list)

    def _get_package_install_rule(self, package_config):
        spec_str = self._get_spec_string(package_config)
        spec_list = self._get_spec_list(package_config)
        extra_flags = self._get_extra_flags(package_config)
        build_env = self._get_build_environment()
        self._logger.debug(msg='Creating package install rule for spec: {0}'.format(spec_str))
        return SubprocessRule(
            self._spack_cmd + ['install', '-v'] + extra_flags + spec_list, env=build_env)

    def _set_compiler_flags(self, spec, flags):
        if os.path.isfile(self._compilers_file):
            with open(self._compilers_file, 'r') as compilers_file:
                compiler_dict = yaml.load(compilers_file, Loader=yaml.SafeLoader)
            for index, compiler in zip(range(len(compiler_dict['compilers'])),
                                       compiler_dict['compilers']):
                if compiler['compiler']['spec'] == spec:
                    compiler_dict['compilers'][index]['compiler']['flags'] = flags
            with open(self._compilers_file, 'w') as compilers_file:
                compilers_file.write(
                    yaml.dump(
                        compiler_dict,
                        default_flow_style=False,
                        Dumper=yaml.SafeDumper
                    ))

    def _show_compilers(self):
        self._logger.info('Following compilers found:')
        if os.path.isfile(self._compilers_file):
            with open(self._compilers_file, 'r') as compilers_file:
                compiler_dict = yaml.load(compilers_file, Loader=yaml.SafeLoader)
            for compiler in compiler_dict['compilers']:
                self._logger.info(compiler['compiler']['spec'])

    def _get_compiler_install_rules(self):
        rules = []
        self._logger.debug(msg='Parsing rules for compilers:')
        compiler_packages = self._confreader['build_config']['compilers']
        rules.append(LoggingRule('Removing old compilers.yml'))
        rules.append(PythonRule(self._remove_compilers_file))

        def get_compiler_find_rule(spec_list):
            return SubprocessRule(
                (self._spack_cmd + ['find', '-p'] +
                 spec_list +
                 (['|', 'tail', '-n', '1', '|', 'awk', "'{",
                   'print', '$2', "}'", '|', 'xargs', '-r']) +
                 self._spack_cmd + ['compiler', 'add']),
                shell=True,
                check=False)

        def get_compiler_flags_rule(spec_list, package_config):
            flags = package_config.get('flags', {})
            return PythonRule(self._set_compiler_flags, [spec_list[0], flags])


        rules.extend([
            LoggingRule('Adding default compilers.'),
            SubprocessRule(
                self._spack_cmd + ['compiler', 'add'],
            )
        ])

        rules.append(LoggingRule('Adding existing compilers.'))
        for package_config in compiler_packages:
            spec_str = self._get_spec_string(package_config)
            spec_list = self._get_spec_list(package_config)
            self._logger.debug(msg='Creating compiler find rule for spec: {0}'.format(spec_str))
            rules.extend([
                get_compiler_find_rule(spec_list),
                get_compiler_flags_rule(spec_list, package_config)
            ])
        rules.append(LoggingRule('Installing compilers.'))
        for package_config in compiler_packages:
            spec_list = self._get_spec_list(package_config)
            if not package_config.get('system_compiler', False):
                rules.extend([
                    self._get_package_install_rule(package_config),
                    get_compiler_find_rule(spec_list),
                    get_compiler_flags_rule(spec_list, package_config)
                ])
        rules.append(PythonRule(self._show_compilers))

        return rules

    def _get_package_install_rules(self):
        rules = []
        self._logger.debug(msg='Parsing rules for packages:')

        packages = self._confreader['build_config']['packages']

        rules.append(LoggingRule('Installing packages.'))
        for package_config in packages:
            rules.extend([
                self._get_package_install_rule(package_config)
            ])

        return rules

    def _copy_license_rule(self, package_config):

        licenses = package_config['licenses']
        spec_list = self._get_spec_list(package_config)
        spec_str = self._get_spec_string(package_config)

        location_args = ['location', '-i'] + spec_list
        install_dir = self._spack_sh(*location_args).splitlines()[0]

        if not install_dir:
            raise Exception(
                'Could not find the installation directory for spec {0}'.format(spec_str))
        license_find_sh = sh.find.bake(install_dir)
        for license in licenses:
            license_files = license_find_sh('-name', license).splitlines()
            if not license_files:
                self._logger.warning(
                    ("No license files found in the installation directory "
                     "of spec '%s' with license file name '%s'."),
                    spec_str,
                    license)
                continue
            for license_file in license_files:
                if not os.path.islink(license_file):
                    continue
                real_path = os.path.realpath(license_file)
                self._logger.info(
                    "Copying license file for package '%s':",
                    spec_str)
                self._logger.info(
                    "License source path: '%s':",
                    real_path)
                self._logger.info(
                    "License target path: '%s':",
                    license_file)
                os.remove(license_file)
                copy_file(real_path, license_file)

    def _get_license_copy_rules(self):

        rules = []
        self._logger.debug(msg='Copying license files:')

        packages = (
            self._confreader['build_config']['packages'] +
            self._confreader['build_config']['compilers']
        )
        for package_config in packages:
            if 'licenses' in package_config:
                rules.append(PythonRule(self._copy_license_rule, [package_config]))

        return rules

    def _get_recreate_modules_rules(self):
        logging_rule = LoggingRule('Recreating modules.')
        recreate_rule = SubprocessRule(
            self._spack_cmd +
            ['module',
             'lmod',
             'refresh',
             '-y',
             '--delete-tree']
            )
        return [logging_rule, recreate_rule]

    def _get_module_arch_folders(self, lmod_root):
        if '$spack' in lmod_root:
            if sh.which('spack'):
                spack_root = self._spack_sh('location', '-r').splitlines()[0]
                lmod_root = lmod_root.replace('$spack', spack_root)

        def is_arch_folder(folder):
            return os.path.isdir(os.path.join(folder, 'Core'))

        arch_folders = [folder for folder in glob(os.path.join(lmod_root, '*'))
                        if is_arch_folder(folder)]

        return arch_folders

    def _remove_all_modules_folders(self, module_root):
        for arch_folder in self._get_module_arch_folders(module_root):
            all_folder = os.path.join(arch_folder, 'all')
            if os.path.isdir(all_folder):
                shutil.rmtree(all_folder)

    def _copy_all_modules(self, module_root):

        def write_module_file_without_modulepath(src, dest):
            with open(src, 'r') as modulefile:
                modulefile_lines = modulefile.readlines()
            with open(dest, 'w') as modulefile_new:
                for line in modulefile_lines:
                    if 'MODULEPATH' not in line:
                        modulefile_new.write(line)
            os.chmod(dest, 0o644)

        copied_modules = {}

        for arch_folder in self._get_module_arch_folders(module_root):

            core_regexp = re.compile(os.path.join(
                arch_folder,
                'Core',
                '(?P<modulename>[^/]+)',
                '(?P<version>[^/]+).lua'))
            mpi_regexp = re.compile(os.path.join(
                arch_folder,
                '(?P<mpi>[^/]+)',
                '(?P<mpi_version>[^/]+)',
                'Core',
                '(?P<modulename>[^/]+)',
                '(?P<version>[^/]+).lua'))

            all_folder = os.path.join(arch_folder, 'all')
            makedirs(all_folder, 0o755)

            corefiles = glob(os.path.join(arch_folder, 'Core', '*', '*.lua'))
            mpifiles = glob(os.path.join(arch_folder, '*', '*', 'Core', '*', '*.lua'))
            moduledict = {x:core_regexp.match(x).groupdict() for x in corefiles}
            moduledict.update({x:mpi_regexp.match(x).groupdict() for x in mpifiles})
            for modulefile, match in moduledict.items():

                modulefolder_new = os.path.join(all_folder, match['modulename'])
                modulefile_new = os.path.join(
                    modulefolder_new,
                    '{}.lua'.format(match['version']))

                if modulefile_new in copied_modules:
                    raise FileExistsError(
                        ('Modulefile overlap encountered. '
                         'Tried to copy modulefile {0} to {1}, but it was also '
                         'copied from modulefile {2}').format(
                             modulefile, modulefile_new, copied_modules[modulefile_new]))

                makedirs(modulefolder_new, 0o755)
                write_module_file_without_modulepath(modulefile, modulefile_new)

                copied_modules[modulefile_new] = match
        self._logger.info(
            'Copied following modules to %s:', all_folder)
        for _, copied_module_info in sorted(copied_modules.items()):
            if 'mpi' in copied_module_info:
                mpi = '%s/%s' % (copied_module_info['mpi'], copied_module_info['mpi_version'])
            else:
                mpi = 'None'
            self._logger.info(
                'Module: %-30s Version: %-30s MPI: %-10s',
                copied_module_info['modulename'],
                copied_module_info['version'],
                mpi)

    def _get_flatten_lmod_rules(self):
        """This function will create rules that generate a flat lmod
        structure from hierarchical modulefiles"""

        lmod_root = self._confreader['config']['config']['module_roots']['lmod']

        rules = [
            LoggingRule(
                'Removing folders that contain the non-hierarchal module structure.'
            ),
            PythonRule(
                self._remove_all_modules_folders,
                args=[lmod_root],
            ),
            LoggingRule(
                'Copying modules to non-hierarchal module structure.'
            ),
            PythonRule(
                self._copy_all_modules,
                args=[lmod_root],
            )
        ]
        return rules

    def _get_rules(self):
        """_get_rules provides build rules for the builder.

        Spack build consists of the following steps:

        1. Reindexing already installed software
        2. Installing compilers
        3. Installing required packages
        4. Copying license files
        5. Re-creating lmod modules to check for name clashes
        6. Creating flat lmod structure

        Returns:
            list: List of build rules.
        """

        rules = (
            self._get_reindex_rules() +
            self._get_compiler_install_rules() +
            self._get_package_install_rules() +
            self._get_license_copy_rules() +
            self._get_recreate_modules_rules() +
            self._get_flatten_lmod_rules()
            )
        return rules

    def _symlink_lmod_modules(self):
        pass

if __name__ == "__main__":

    CONF_FOLDER = sys.argv[1]

    BUILDER = SpackBuilder(CONF_FOLDER)
    BUILDER.describe()
