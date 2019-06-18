# -*- coding=utf-8 -*-
"""Utilies for tests."""

import os
import warnings
import logging
from collections import defaultdict
from functools import wraps
from io import StringIO
import sys

def count_log_events(capture):
    """This function counts how many logging events occured
    in a capture done with testfixtures.log_capture.

    Args:
        capture (object): Log capture object.

    Returns:
        dict: Dict with the number of events.
    """
    event_types = [log_event[1] for log_event in capture.actual()]

    event_counts = defaultdict(int)

    for event in event_types:
        event_counts[event] += 1

    return event_counts


def ignore_deprecationwarning(func):
    """This decorator causes function to ignore DeprecationWarnings.

    Args:
        func (function): Function to decorate.

    Returns:
        function: Decorated function.
    """
    @wraps(func)
    def inner(*args, **kwargs):
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            response = func(*args, **kwargs)
        return response
    return inner

def example_function(val1=1, val2=2):
    """Example Python function that can be used for various calls."""
    return val1 + val2

EXAMPLE_CONFIGS = dict(
    (configname, os.path.join('tests', 'examples', '{0}.yaml'.format(configname)))
    for configname in ['deployment_config']
)

EXAMPLE_SCHEMAS = {
    'deployment_config': {
        "type": "object",
        "properties": {
            "method": {"type": "string"},
            "delete": {"type": "boolean"},
            "set_sbit": {"type": "boolean"},
            "target_host": {"type": "string"},
        },
        "required": ["method", "delete", "set_sbit", "target_host"],
        "maxProperties": 4
    }
}
