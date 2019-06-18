# -*- coding: utf-8 -*-
"""buildrules contains various build setups.

buildrules contains various build setups. Running this module will create
a desired builder and afterwards it will run a command on it.
"""
import os
import logging
from argparse import ArgumentParser
import buildrules as br
from buildrules.common.logging import get_logger

def run_builder(builder, cmd, conf_folder):
    """runBuilder runs a Builder instance.

    Args:
        builder (str): Name of the builder class.
        cmd (str): Command to run.
        conf_folder (str): Configuration folder for the builder.

    Raises:
        ValueError: When invalid configuration folder is given.
    """

    if not os.path.isdir(conf_folder):
        raise ValueError(
            'Invalid configuration folder: {0}'.format(conf_folder))

    builder_instance = br.BUILDERS[builder](conf_folder)

    if cmd == 'describe':
        builder_instance.describe()
    elif cmd == 'build':
        builder_instance()


if __name__ == "__main__":

    PARSER = ArgumentParser()
    PARSER.add_argument(
        'builder',
        nargs=1,
        type=str,
        help='Builder to use',
        choices=br.BUILDERS.keys())
    PARSER.add_argument(
        'cmd',
        nargs=1,
        type=str,
        help='Command to run',
        choices=('build', 'describe'))
    PARSER.add_argument(
        'conf_folder',
        nargs=1,
        type=str,
        help='Configuration folder for builder')
    PARSER.add_argument(
        '-l',
        '--loglevel',
        nargs=1,
        type=str,
        help='Logging level to use',
        default=['INFO']
        )

    ARGS = PARSER.parse_args()

    get_logger(ARGS.loglevel[0])

    run_builder(ARGS.builder[0], ARGS.cmd[0], os.path.expanduser(ARGS.conf_folder[0]))
