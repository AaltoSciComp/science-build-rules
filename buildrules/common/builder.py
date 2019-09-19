# -*- coding: utf-8 -*-
"""Builder runs buildrules.

This module contains base Builder class used by various buildrules to
actually build software.
"""
import os
import sys
import logging
import hashlib
from shutil import copy2, copytree
import json
from jinja2 import Template

from buildrules.common.errors import log_error_and_quit
from buildrules.common.confreader import ConfReader
from buildrules.common.rule import Rule, RuleError
from buildrules.common.deployer import deployer_factory, Deployer, DEPLOYMENTCONFIG_SCHEMA

class Builder:
    """This superclass will create a build based on buildrules.

    Builder is initialized based on given configuration files and schemas of
    said configurations. It checks the validity of the configurations using
    ConfReader. Deployment strategy is based on 'deployment_config' and
    created using deployer_factory.

    'buildrules' are created using _get_rules-function. Subclasses of Builder
    should overwrite this function.

    An overview of the whole build can be obtained with describe-function.

    Build is initialized by running the Builder. By specifying dry_run no
    changes are made, but the output is presented.

    Args:
        conf_folder (str): Configuration folder that contains configuration
        files.
    """

    BUILDER_NAME = 'None'
    CONF_FILES = []
    SCHEMAS = []

    @log_error_and_quit
    def __init__(self, conf_folder):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._conf_files = list(
            map(lambda x: os.path.join(conf_folder,x), self.CONF_FILES + ['deployment_config.yaml'])
        )
        self._schemas = self.SCHEMAS + [DEPLOYMENTCONFIG_SCHEMA]
        self._confreader = ConfReader(self._conf_files, self._schemas)
        self._deployers = deployer_factory(self._confreader)

    def _skip_rule(self, step):
        return step in self._confreader.get('build_config',{}).get('skip_rules',[])

    def __call__(self, dry_run=False):
        """This function will execute all _build_rules."""
        rules = self._get_rules()

        for deployer in self._deployers:
            rules = rules + deployer.get_rules()

        for rule in rules:
            try:
                rule(dry_run=dry_run)
            except RuleError as e:
                self._logger.error('Encountered an error while executing BuildRule: {0}: {1}'.format(rule, e))
                sys.exit(1)

    def _get_rules(self):
        """"""
        return []

    @log_error_and_quit
    def describe(self):
        """"""
        self._logger.info('Builder: {0}'.format(self.BUILDER_NAME))
        self._logger.info(
            'Configuration files: {0}'.format(' '.join(self.CONF_FILES + ['deployment_config.yaml'])))
        self._logger.debug(str(self._confreader))

        rules = self._get_rules()

        self._logger.info('Build rule descriptions:')
        for rule in rules:
            self._logger.info(rule)

        deployer_rules = []
        deployers = deployer_factory(self._confreader)
        for deployer in deployers:
            deployer_rules = deployer_rules + deployer.get_rules()

        self._logger.info('Deployment descriptions:')
        for rule in deployer_rules:
            self._logger.info(rule)

    @classmethod
    def _makedirs(cls, path, chmod=None):
        """ This function creates a folder with requested permissions

        Args:
            path (str): Folder to create.
            chmod (str): Chmod permissions. Default is None.
        """
        try:
            os.makedirs(path)
            if chmod:
                os.chmod(path, chmod)
        except FileExistsError:
            pass

    @classmethod
    def _copy_file(cls, src, target, chmod=None):
        """ This function copies a file from src to target with required
        permissions.

        Args:
            src (str): File that will be copied.
            target (str): Target folder / file.
            chmod (str): Chmod permissions. Default is None.
        """
        copy2(src, target)
        if chmod:
            os.chmod(target, chmod)
    
    @classmethod
    def _copy_dir(cls, src, target, chmod=None):
        """ This function copies a folder from src to target with required
        permissions.

        Args:
            src (str): Folder that will be copied.
            target (str): Target folder.
            chmod (str): Chmod permissions. Default is None.
        """
        copytree(src, target, symlinks=True)
        if chmod:
            os.chmod(target, chmod)

    def _write_template(self, target_path, template_path=None, template=None):
        """Writes a file based on jinja2-template.

        Args:
            target_path (str): Target path to fill.
            template_path (str): Template file to use. Default None.
            template (str): jinja2-template as a string. Default None.
        """
        if not template:
            with open(template_path, 'r') as template_file:
                template = ''.join(template_file.readlines())
        filled_template = self._fill_template(template)
        with open(target_path, 'w') as target_file:
            target_file.write(filled_template)

    def _fill_template(self, template):
        """Fills a jinja2-template based on build_config.

        Args:
            template (str): jinja2-template as a string.
        Returns:
            str: Filled template.
        """
        return Template(template).render(self._confreader['build_config'])

    def _calculate_file_checksum(self, filename, hash_function='sha256'):
        hash_functions = {
            'sha256': hashlib.sha256
        }
        hash_function = hash_functions[hash_function]()
        with open(filename, "rb") as input_file:
            for byte_block in iter(lambda: input_file.read(4096), b""):
                hash_function.update(byte_block)

        return hash_function.hexdigest()

    def _calculate_dict_checksum(self, dict_object, hash_function='sha256'):
        hash_functions = {
            'sha256': hashlib.sha256
        }
        hash_function = hash_functions[hash_function]()
        json_dump = json.dumps(dict_object, ensure_ascii=False, sort_keys=True)
        hash_function.update(json_dump.encode('utf-8'))

        return hash_function.hexdigest()
