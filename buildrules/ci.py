# -*- coding: utf-8 -*-
"""SpackBuilder is a builder that builds using spack.
"""
import os
import logging
import tempfile

from buildrules.common.builder import Builder
from buildrules.common.rule import PythonRule, SubprocessRule, LoggingRule, RuleError

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
                    'fqdn': {'type': 'string'},
                    'private_key': {'type': 'string'},
                    'public_cert':  {'type': 'string'},
                    'web_port': {'type': 'integer'},
                    'gitlab_hook_secret': {'type': 'string'},
                    'github_hook_secret': {'type': 'string'},
                    'github_token_secret': {'type': 'string'},
                    'worker_password': {'type': 'string'},
                    'worker_port': {'type': 'integer'},
                    'timeout': {'type': 'integer'},
                    'worker_uid': {'type': 'integer'},
                },
                'required': [
                    'image',
                    'fqdn',
                    'worker_password',
                    'worker_uid'
                ],
            },
            'auths': {
                'type': 'object',
                'properties': {
                    'ssh': {
                        'type': 'object',
                        'properties': {
                            'config_file': {'type': ['string', 'null']},
                            'known_hosts_file': {'type': ['string', 'null']},
                            'private_keys': {
                                'type': ['array', 'null'],
                                'items': {'type': 'string'}
                            },
                            'public_keys': {
                                'type': ['array', 'null'],
                                'items': {'type': 'string'}
                            },
                        },
                    },
                    'docker': {
                        'type': 'object',
                        'properties': {
                            'config_file': {'type': 'string'},
                        },
                    },
                    'singularity': {
                        'type': 'object',
                        'properties': {
                            'config_file': {'type': 'string'},
                        },
                    },
                },
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
                        'spack': {
                            'type': 'object',
                            'properties': {
                                'target_path:': {'type': 'string'},
                                'url': {'type': 'string'},
                                'branch': {'type': 'string'},
                                'github_hook': {'type': 'boolean'},
                                'schedule': {
                                    'type': 'object',
                                    'properties': {
                                        'hour': {'type':'integer'},
                                        'minute': {'type':'integer'},
                                        'dayOfMonth': {'type':'integer'},
                                        'month': {'type':'integer'},
                                        'dayOfWeek': {'type':'integer'},
                                    },
                                },
                            },
                        },
                        'singularity': {
                            'type': 'object',
                            'properties': {
                                'target_path:': {'type': 'string'},
                                'github_hook': {'type': 'boolean'},
                                'schedule': {
                                    'type': 'object',
                                    'properties': {
                                        'hour': {'type':'integer'},
                                        'minute': {'type':'integer'},
                                        'dayOfMonth': {'type':'integer'},
                                        'month': {'type':'integer'},
                                        'dayOfWeek': {'type':'integer'},
                                    },
                                },
                            },
                        },
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
        self._nfs_folder = os.path.join(
            self._confreader['build_config']['build_folder'],
            'nfs')

    def _get_clone_build_environment_rule(self):
        """Clones build environment into a temporary directory"""
        if not os.path.isdir(self._build_folder):
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
            LoggingRule('Creating nginx.conf'),
            PythonRule(
                self._write_template,
                args=[
                    os.path.join(
                        self._conf_folder,
                        'nginx',
                        'nginx.conf'
                    ),
                    os.path.join(
                        self._templates_folder,
                        'nginx.conf.j2'
                    ),
                ],
            ),
            LoggingRule('Creating exports.txt'),
            PythonRule(
                self._write_template,
                args=[
                    os.path.join(
                        self._conf_folder,
                        'nfs',
                        'exports.txt'
                    ),
                    os.path.join(
                        self._templates_folder,
                        'exports.txt.j2'
                    ),
                ],
            ),
        ]

    def _get_directory_creation_rules(self):
        """Creates directories for nfs"""
        rules = [LoggingRule('Creating build directories')]

        workers = [{'name':'master', 'builds': {}}]

        workers.extend(self._confreader['build_config']['target_workers'])

        for worker in workers:
            worker_home_folder = os.path.join(
                self._nfs_folder,
                'buildbot_home',
                worker['name'])
            worker_ssh_folder = os.path.join(
                worker_home_folder,
                '.ssh')
            rules.extend([
                LoggingRule(
                    ('Creating nfs home directory '
                     'for worker %s') % worker['name']
                ),
                PythonRule(
                    self._makedirs,
                    args=[worker_ssh_folder],
                    kwargs={'chmod':0o700}),
                LoggingRule('Creating .bashrc'),
                PythonRule(
                    self._write_template,
                    args=[
                        os.path.join(
                            worker_home_folder,
                            '.bashrc'
                        ),
                        os.path.join(
                            self._templates_folder,
                            'bashrc.j2'
                        ),
                    ]
                ),
                LoggingRule(
                    ('Creating build and software '
                     'directories for worker %s') % worker['name'])
            ])
            for builder_name, builder_opts in self._confreader['build_config']['builds'].items():
                if builder_opts.get('enabled', False):
                    rules.extend([
                        PythonRule(
                            self._makedirs,
                            args=[
                                os.path.join(
                                    self._nfs_folder,
                                    'builds',
                                    worker['name'],
                                    builder_name
                                ),
                            ],
                        ),
                        PythonRule(
                            self._makedirs,
                            args=[
                                os.path.join(
                                    self._nfs_folder,
                                    'software',
                                    worker['name'],
                                    builder_name
                                ),
                            ],
                        ),
                    ])
        return rules

    def _copy_certs(self):

        fqdn = self._confreader['build_config']['buildbot_master']['fqdn']
        private_key = self._confreader['build_config']['buildbot_master'].get('private_key', None)
        public_cert = self._confreader['build_config']['buildbot_master'].get('public_cert', None)
        key = os.path.join(self._build_folder, 'certs', 'buildbot.key')
        cert = os.path.join(self._build_folder, 'certs', 'buildbot.crt')

        rules = []

        if private_key and public_cert:

            rules.extend([
                LoggingRule('Copying certs'),
                PythonRule(
                    self._copy_file,
                    args=[
                        self._confreader['build_config']['buildbot_master']['private_key'],
                        key
                    ]
                ),
                PythonRule(
                    self._copy_file,
                    args=[
                        self._confreader['build_config']['buildbot_master']['public_cert'],
                        cert
                    ]
                )
            ])
        else:
            rules.extend([
                LoggingRule('Creating self signed certs', self._logger.warning),
                SubprocessRule(
                    ['openssl', 'req', '-x509', '-nodes', '-new',
                     '-keyout', key, '-out', cert,
                     '-days', '365', '-subj', '/CN=%s' % fqdn],
                    stderr_writer=self._logger.warning
                    )
            ])

        rules.extend([
            LoggingRule('Setting cert modes'),
            PythonRule(os.chmod,
                       args=[key, 0o600]),
            PythonRule(os.chmod,
                       args=[cert, 0o644])
        ])


        return rules

    def _copy_ssh(self):
        """Copies or creates ssh keys based on configuration"""

        rules = []

        workers = [{'name':'master', 'builds': {}}]

        workers.extend(self._confreader['build_config']['target_workers'])

        auth_ssh_conf = self._confreader['build_config'].get('auths', {}).get('ssh', {})

        ssh_config_src = auth_ssh_conf.get('config_file', None)
        known_hosts_src = auth_ssh_conf.get('known_hosts_file', None)

        private_keys = auth_ssh_conf.get('private_keys', [])
        public_keys = auth_ssh_conf.get('public_keys', [])

        for worker in workers:

            ssh_folder = os.path.join(
                self._build_folder,
                'nfs',
                'buildbot_home',
                worker['name'],
                '.ssh')

            rules.append(LoggingRule(
                ('Copying ssh settings '
                 'to home folder of %s') % worker['name']
            ))
            if ssh_config_src:
                ssh_config_target = os.path.join(ssh_folder, 'config')
                rules.extend([
                    PythonRule(
                        self._copy_file,
                        args=[
                            ssh_config_src,
                            ssh_config_target
                        ],
                        kwargs={'chmod':0o644})
                ])
            if known_hosts_src:
                known_hosts_target = os.path.join(ssh_folder, 'known_hosts')
                rules.extend([
                    PythonRule(
                        self._copy_file,
                        args=[
                            known_hosts_src,
                            known_hosts_target
                        ],
                        kwargs={'chmod':0o600})
                ])

            if public_keys:
                for public_key_src in public_keys:
                    public_key_target = os.path.join(
                        ssh_folder,
                        os.path.basename(public_key_src)
                    )
                    rules.extend([
                        PythonRule(
                            self._copy_file,
                            args=[
                                public_key_src,
                                public_key_target
                            ],
                            kwargs={'chmod':0o644})
                    ])

            if private_keys:
                for private_key_src in private_keys:
                    private_key_target = os.path.join(
                        ssh_folder,
                        os.path.basename(private_key_src)
                    )
                    rules.extend([
                        PythonRule(
                            self._copy_file,
                            args=[
                                private_key_src,
                                private_key_target
                            ],
                            kwargs={'chmod':0o600})
                    ])
            else:
                private_key_target = os.path.join(
                    ssh_folder,
                    'id_rsa_autogen'
                )
                if os.path.isfile(private_key_target):
                    rules.append(
                        LoggingRule(
                            ('Autogenerated ssh key '
                             '{0} exists. Skipping key '
                             'generation.').format(private_key_target),
                            stdout_writer=self._logger.warning)
                        )

                else:
                    rules.extend([
                        LoggingRule('No private keys given, generating them.',
                                    stdout_writer=self._logger.warning),
                        SubprocessRule(
                            ['ssh-keygen', '-t', 'rsa', '-b', '4096', '-N', '""',
                             '-q', '-f', private_key_target],
                            shell=True
                        )
                    ])

                    # Adding newly generated keys to key lists so that they
                    # will be cloned to other workers
                    private_keys.append(private_key_target)
                    public_keys.append('%s.pub' % private_key_target)

        return rules

    def _get_rules(self):
        rules = []
        rules.extend(self._get_clone_build_environment_rule())
        rules.extend(self._get_directory_creation_rules())
        rules.extend(self._copy_certs())
        rules.extend(self._copy_ssh())
        rules.extend(self._get_config_creation_rules())
        return rules

if __name__ == "__main__":
    import sys

    CONF_FOLDER = sys.argv[1]

    CI_BUILDER = CIBuilder(CONF_FOLDER)
    CI_BUILDER.describe()
