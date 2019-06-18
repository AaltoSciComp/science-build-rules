# -*- coding: utf-8 -*-
"""Logging contains helper functions related to logging.
"""
import os
import coloredlogs

def get_logger(loglevel='INFO'):
    """getLogger creates a logger based on logconfig.

    Args:
        loglevel (str): Loglevel to use. Default is 'INFO'.
    """
    coloredlogs.install(
        level=loglevel,
        fmt='%(asctime)s %(hostname)s %(name)s %(levelname)s %(message)s'
    )
