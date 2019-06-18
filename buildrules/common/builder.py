# -*- coding: utf-8 -*-
"""Builder runs buildrules.

This module contains base Builder class used by various buildrules to
actually build software.
"""
import os
import logging

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

    def __init__(self, conf_folder):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._conf_files = list(
            map(lambda x: os.path.join(conf_folder,x), self.CONF_FILES + ['deployment_config.yaml'])
        )
        self._schemas = self.SCHEMAS + [DEPLOYMENTCONFIG_SCHEMA]
        self._confreader = ConfReader(self._conf_files, self._schemas)
        self._deployers = deployer_factory(self._confreader)

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
                raise e

    def _get_rules(self):
        """"""
        return []

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
