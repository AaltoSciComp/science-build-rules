# -*- coding: utf-8 -*-
"""Deployer deploys software..

This module contains Deployer-classes that deploy software and a 
deployer_factory function used by Builder to choose between deployment
strategies.
"""
import logging
import os
from jsonschema import validate
from buildrules.common.rule import SubprocessRule, LoggingRule

DEPLOYMENTCONFIG_SCHEMA = {
    "$schema" : "http://json-schema.org/draft-07/schema#",
    "type" : "array",
    "default" : [],
    "items" : {
        "type" : "object",
        "properties" : {
            "method": {"type" : "string"}
        },
        "required": ["method"]
    }
}

class Deployer:

    DEPLOYER_SCHEMA = {
        "$schema" : "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties" : {
            "method": {"type" : "string"},
            "target_host": {"type" : "string"}
        },
        "required": ["method", "target_host"]
    }
    """This class will deploy installed software.

    Args:
        deployer_config (dict): Configuration that contains releavant fields
        defined in DEPLOYMENTCONFIG_SCHEMAS.
    """

    def __init__(self, deployer_config):
        validate(deployer_config, self.DEPLOYER_SCHEMA) 
        self._deployer_config = deployer_config
        self._deployment_command=self.deployment_command()

    def __str__(self):
        return "sp_function: {0}".format(self._deployment_command)

    def deployment_command(self):
        pass

    def get_rules(self):
        rules = []
        rules.append(LoggingRule('Deploying software'))
        rules.append(self._deployment_command)
        return rules

class RsyncDeployer(Deployer):

    DEPLOYER_SCHEMA = {
        "$schema" : "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties" : {
            "method": {"type" : "string"},
            "target_host": {"type" : "string"},
            "source": {"type" : "string"},
            "dest": {"type" : "string"},
            "working_directory": {"type" : "string"},
            "chmod_options": {"type" : "string"},
            "rsync_flags": {"type" : "string"},
            "ssh_command": {"type" : "string"},
            "delete": {"type" : "boolean"}
        },
        "required": ["method", "target_host", "source", "dest"]
    }

    DEFAULT_CONFIGS = {
        "rsync_flags": "-surlptDxv",
        "chmod_options": None,
        "ssh_command": "ssh",
        "delete": False,
        "working_directory": None
    }

    def deployment_command(self, dry_run=False):
        rsync_deployer_config = self.DEFAULT_CONFIGS.copy()
        rsync_deployer_config.update(**self._deployer_config)

        cmd = ['rsync']
        cmd.append(rsync_deployer_config['rsync_flags'])
        if rsync_deployer_config['chmod_options']:
            cmd.append('--chmod={0}'.format(rsync_deployer_config['chmod_options']))
        cmd.extend(['-e',rsync_deployer_config['ssh_command']])
        if rsync_deployer_config['delete']:
            cmd.append('--delete')

        rsync_cwd = rsync_deployer_config['working_directory']
        if rsync_cwd:
            src = os.path.relpath(rsync_deployer_config['source'], rsync_cwd)
        else:
            src = rsync_deployer_config['source']

        target = '{0}:"{1}"'.format(rsync_deployer_config['target_host'],rsync_deployer_config['dest'])
        src = '"{0}/"'.format(src)
        
        return SubprocessRule(cmd + [src, target], shell=True, cwd=rsync_cwd)

        

def deployer_factory(confreader):
    """This function creates instances of subclasses of Deployer based on
    deployment_config. The configurations passed to the deployers class are validated 
    again against the specific schema of each class.
    """

    confreader.validate('deployment_config', DEPLOYMENTCONFIG_SCHEMA)

    deployer_classes = {'rsync' : RsyncDeployer}

    deployers = []
    for deployer_config in confreader['deployment_config']:
        deployers.append(deployer_classes[deployer_config['method']](deployer_config))

    return deployers
