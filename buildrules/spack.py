# -*- coding: utf-8 -*-
"""SpackBuilder is a builder that builds using spack.
"""
import sys
import os
import logging
import yaml

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule

class SpackBuilder(Builder):
    """SpackBuilder extends on Builder and creates buildrules for Spack build.
    """

    BUILDER_NAME = 'Spack'
    CONF_FILES = ['config.yaml', 'modules.yaml', 'packages.yaml', 'build_config.yaml']
    SCHEMAS = [
        {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Spack core configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                'config': {
                    'type': 'object',
                    'default': {},
                    'properties': {
                        'install_tree': {'type': 'string'},
                        'install_hash_length': {'type': 'integer', 'minimum': 1},
                        'install_path_scheme': {'type': 'string'},
                        'build_stage': {
                            'oneOf': [
                                {'type': 'string'},
                                {'type': 'array',
                                 'items': {'type': 'string'}}],
                        },
                        'template_dirs': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        },
                        'module_roots': {
                            'type': 'object',
                            'additionalProperties': False,
                            'properties': {
                                'tcl': {'type': 'string'},
                                'lmod': {'type': 'string'},
                                'dotkit': {'type': 'string'},
                            },
                        },
                        'source_cache': {'type': 'string'},
                        'misc_cache': {'type': 'string'},
                        'verify_ssl': {'type': 'boolean'},
                        'debug': {'type': 'boolean'},
                        'checksum': {'type': 'boolean'},
                        'locks': {'type': 'boolean'},
                        'dirty': {'type': 'boolean'},
                        'build_jobs': {'type': 'integer', 'minimum': 1},
                        'ccache': {'type': 'boolean'},
                    }
                },
            },
        }, {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Spack module file configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'definitions': {
                'array_of_strings': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'string'
                    }
                },
                'dictionary_of_strings': {
                    'type': 'object',
                    'patternProperties': {
                        r'\w[\w-]*': {  # key
                            'type': 'string'
                        }
                    }
                },
                'dependency_selection': {
                    'type': 'string',
                    'enum': ['none', 'direct', 'all']
                },
                'module_file_configuration': {
                    'type': 'object',
                    'default': {},
                    'additionalProperties': False,
                    'properties': {
                        'filter': {
                            'type': 'object',
                            'default': {},
                            'additionalProperties': False,
                            'properties': {
                                'environment_blacklist': {
                                    'type': 'array',
                                    'default': [],
                                    'items': {
                                        'type': 'string'
                                    }
                                }
                            }
                        },
                        'template': {
                            'type': 'string'
                        },
                        'autoload': {
                            '$ref': '#/definitions/dependency_selection'},
                        'prerequisites': {
                            '$ref': '#/definitions/dependency_selection'},
                        'conflict': {
                            '$ref': '#/definitions/array_of_strings'},
                        'load': {
                            '$ref': '#/definitions/array_of_strings'},
                        'suffixes': {
                            '$ref': '#/definitions/dictionary_of_strings'},
                        'environment': {
                            'type': 'object',
                            'default': {},
                            'additionalProperties': False,
                            'properties': {
                                'set': {
                                    '$ref': '#/definitions/dictionary_of_strings'},
                                'unset': {
                                    '$ref': '#/definitions/array_of_strings'},
                                'prepend_path': {
                                    '$ref': '#/definitions/dictionary_of_strings'},
                                'append_path': {
                                    '$ref': '#/definitions/dictionary_of_strings'}
                            }
                        }
                    }
                },
                'module_type_configuration': {
                    'type': 'object',
                    'default': {},
                    'anyOf': [
                        {'properties': {
                            'verbose': {
                                'type': 'boolean',
                                'default': False
                            },
                            'hash_length': {
                                'type': 'integer',
                                'minimum': 0,
                                'default': 7
                            },
                            'whitelist': {
                                '$ref': '#/definitions/array_of_strings'},
                            'blacklist': {
                                '$ref': '#/definitions/array_of_strings'},
                            'blacklist_implicits': {
                                'type': 'boolean',
                                'default': False
                            },
                            'naming_scheme': {
                                'type': 'string'  # Can we be more specific here?
                            }
                        }},
                        {'patternProperties': {
                            r'\w[\w-]*': {
                                '$ref': '#/definitions/module_file_configuration'
                            }
                        }}
                    ]
                }
            },
            'patternProperties': {
                r'modules': {
                    'type': 'object',
                    'default': {},
                    'additionalProperties': False,
                    'properties': {
                        'prefix_inspections': {
                            'type': 'object',
                            'patternProperties': {
                                # prefix-relative path to be inspected for existence
                                r'\w[\w-]*': {
                                    '$ref': '#/definitions/array_of_strings'}}},
                        'enable': {
                            'type': 'array',
                            'default': [],
                            'items': {
                                'type': 'string',
                                'enum': ['tcl', 'dotkit', 'lmod']}},
                        'lmod': {
                            'allOf': [
                                # Base configuration
                                {'$ref': '#/definitions/module_type_configuration'},
                                {
                                    'core_compilers': {
                                        '$ref': '#/definitions/array_of_strings'
                                    },
                                    'hierarchical_scheme': {
                                        '$ref': '#/definitions/array_of_strings'
                                    }
                                }  # Specific lmod extensions
                            ]},
                        'tcl': {
                            'allOf': [
                                # Base configuration
                                {'$ref': '#/definitions/module_type_configuration'},
                                {}  # Specific tcl extensions
                            ]},
                        'dotkit': {
                            'allOf': [
                                # Base configuration
                                {'$ref': '#/definitions/module_type_configuration'},
                                {}  # Specific dotkit extensions
                            ]},
                        }
                    },
                },
        }, {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Spack package configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                r'packages': {
                    'type': 'object',
                    'default': {},
                    'additionalProperties': False,
                    'patternProperties': {
                        r'\w[\w-]*': {  # package name
                            'type': 'object',
                            'default': {},
                            'additionalProperties': False,
                            'properties': {
                                'version': {
                                    'type': 'array',
                                    'default': [],
                                    # version strings
                                    'items': {'anyOf': [{'type': 'string'},
                                                        {'type': 'number'}]}},
                                'compiler': {
                                    'type': 'array',
                                    'default': [],
                                    'items': {'type': 'string'}},  # compiler specs
                                'buildable': {
                                    'type':  'boolean',
                                    'default': True,
                                },
                                'permissions': {
                                    'type': 'object',
                                    'additionalProperties': False,
                                    'properties': {
                                        'read': {
                                            'type':  'string',
                                            'enum': ['user', 'group', 'world'],
                                        },
                                        'write': {
                                            'type':  'string',
                                            'enum': ['user', 'group', 'world'],
                                        },
                                        'group': {
                                            'type':  'string',
                                        },
                                    },
                                },
                                'modules': {
                                    'type': 'object',
                                    'default': {},
                                },
                                'providers': {
                                    'type':  'object',
                                    'default': {},
                                    'additionalProperties': False,
                                    'patternProperties': {
                                        r'\w[\w-]*': {
                                            'type': 'array',
                                            'default': [],
                                            'items': {'type': 'string'}, }, }, },
                                'paths': {
                                    'type': 'object',
                                    'default': {},
                                },
                                'variants': {
                                    'oneOf': [
                                        {'type': 'string'},
                                        {'type': 'array',
                                         'items': {'type': 'string'}}],
                                },
                            },
                        },
                    },
                },
            },
        }, {
            '$schema': 'http://json-schema.org/schema#',
            'title': 'Package configuration file schema',
            'type': 'object',
            'additionalProperties': False,
            'patternProperties': {
                'compilers': {
                    'type': 'array',
                    'default': [],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'version': {'type': 'string'},
                            'system_compiler': {'type': 'boolean'},
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
        self._compilers_file = os.path.expanduser('~/.spack/linux/compilers.yaml')
        super().__init__(conf_folder)

    def _get_reindex_rules(self):
        logging_rule = LoggingRule('Re-indexing installed packages')
        reindex_rule = SubprocessRule(self._spack_cmd + ['reindex'])
        return [logging_rule, reindex_rule]

    def _get_spec_string(self, package_config):
        return ' '.join(self._get_spec_list(package_config))

    @classmethod
    def _get_spec_list(cls, package_config):
        spec_list = ['{name}@{version}'.format(**package_config)]
        spec_list.extend(package_config.get('variants', []))
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
        self._logger.debug(msg='Creating package install rule for spec: {0}'.format(spec_str))
        return SubprocessRule(self._spack_cmd + ['install', '-v'] + spec_list)

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
            LoggingRule('Adding default compilers'),
            SubprocessRule(
                self._spack_cmd + ['compiler', 'add'],
            )
        ])

        rules.append(LoggingRule('Adding existing compilers'))
        for package_config in compiler_packages:
            spec_str = self._get_spec_string(package_config)
            spec_list = self._get_spec_list(package_config)
            self._logger.debug(msg='Creating compiler find rule for spec: {0}'.format(spec_str))
            rules.extend([
                get_compiler_find_rule(spec_list),
                get_compiler_flags_rule(spec_list, package_config)
            ])
        rules.append(LoggingRule('Installing compilers'))
        for package_config in compiler_packages:
            if not package_config.get('system_compiler', False):
                rules.extend([
                    self._get_package_install_rule(package_config),
                    get_compiler_find_rule(spec_list),
                    get_compiler_flags_rule(spec_list, package_config)
                ])

        return rules

    def _get_package_install_rules(self):
        rules = []
        self._logger.debug(msg='Parsing rules for packages:')

        packages = self._confreader['build_config']['packages']

        rules.append(LoggingRule('Installing packages'))
        for package_config in packages:
            rules.extend([
                self._get_package_install_rule(package_config)
            ])

        return rules

    def _get_license_copy_rules(self):
        return []

    def _get_recreate_modules_rules(self):
        logging_rule = LoggingRule('Recreating modules')
        recreate_rule = SubprocessRule(
            self._spack_cmd +
            ['module',
             'lmod',
             'refresh',
             '-y',
             '--delete-tree']
            )
        return [logging_rule, recreate_rule]

    def _get_symlink_modules_rules(self):
        return []

    def _get_rules(self):
        """_get_rules provides build rules for the builder.

        Spack build consists of the following steps:

        1. Reindexing already installed software
        2. Installing compilers

        """

        rules = (
            self._get_reindex_rules() +
            self._get_compiler_install_rules() +
            self._get_package_install_rules() +
            self._get_license_copy_rules() +
            self._get_recreate_modules_rules() +
            self._get_symlink_modules_rules()
            )
        return rules

    def _symlink_lmod_modules(self):
        pass

if __name__ == "__main__":

    CONF_FOLDER = sys.argv[1]

    SPACK_BUILDER = SpackBuilder(CONF_FOLDER)
    SPACK_BUILDER.describe()
