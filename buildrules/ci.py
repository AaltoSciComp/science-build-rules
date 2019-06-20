# -*- coding: utf-8 -*-
"""SpackBuilder is a builder that builds using spack.
"""
import os
import logging

from buildrules.common.builder import Builder

class CIBuilder(Builder):

    """CIBuilder extends on Builder and creates CI environment for running buildrules.
    """
    BUILDER_NAME = 'CI'
    CONF_FILES = ['build_config.yaml']
    SCHEMAS = [{}]


    def _get_rules(self):
        return []

if __name__ == "__main__":
    import sys

    CONF_FOLDER = sys.argv[1]

    CI_BUILDER = CIBuilder(CONF_FOLDER)
    CI_BUILDER.describe()
