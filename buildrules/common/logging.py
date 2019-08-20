# -*- coding: utf-8 -*-
"""Logging contains helper functions related to logging.
"""
import os
import re
import logging
import coloredlogs

class ShFilter(logging.Filter):

    def __init__(self):

        self._command_reg = re.compile("<Command .*>: ")

    def filter(self, record):

        allow = self._command_reg.search(record.msg) is None

        return allow

def get_logger(loglevel='INFO'):
    """getLogger creates a logger based on logconfig.

    Args:
        loglevel (str): Loglevel to use. Default is 'INFO'.
    """
    coloredlogs.install(
        level=loglevel,
        fmt='%(asctime)s %(hostname)s %(name)s %(levelname)s %(message)s'
    )
    sh_logger = logging.getLogger('sh.command')

    shfilter = ShFilter()
    sh_logger.addFilter(shfilter)
