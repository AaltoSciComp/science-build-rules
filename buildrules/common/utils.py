# -*- coding: utf-8 -*-
"""Utils contains various useful utilities for builders.
"""
import os
import re
import hashlib
import json
import textwrap
from shutil import copy2, copytree
import yaml
from jinja2 import Template

class YAMLDumper(yaml.SafeDumper):

    def increase_indent(self, flow=False, indentless=False):
        return super(YAMLDumper, self).increase_indent(flow, False)

def remove_tabs(string):
    return re.sub('\t', '  ', string)

def get_formatted_yaml(contents):
    return remove_tabs(
        yaml.dump(
            contents,
            default_flow_style=False,
            Dumper=YAMLDumper))

def write_yaml(filename, contents):
    with open(filename, 'w') as yaml_file:
        yaml_file.write(get_formatted_yaml(contents))

def load_yaml(filename):
    with open(filename, 'r') as yaml_file:
        contents = yaml.load(yaml_file, Loader=yaml.SafeLoader)
    return contents

def makedirs(path, chmod=None):
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

def copy_file(src, target, chmod=None):
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

def copy_dir(src, target, chmod=None):
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

def fill_template(template, config):
    """Fills a jinja2-template based on configuration dict.

    Args:
        template (str): jinja2-template as a string.
        config (dict): Dictionary to use for filling the template.
    Returns:
        str: Filled template.
    """
    return Template(textwrap.dedent(template)).render(config).strip()

def write_template(target_path, config, template_path=None, template=None, chmod=None):
    """Writes a file based on jinja2-template.

    Args:
        target_path (str): Target path to fill.
        config (dict): Dictionary to use for filling the template.
        template_path (str): Template file to use. Default None.
        template (str): jinja2-template as a string. Default None.
        chmod (str): Chmod permissions. Default is None.
    """
    if not template and not template_path:
        raise ValueError('Both template_path and template cannot be empty')
    if not template:
        with open(template_path, 'r') as template_file:
            template = ''.join(template_file.readlines())
    filled_template = fill_template(template, config)
    with open(target_path, 'w') as target_file:
        target_file.write(filled_template)
    if chmod:
        os.chmod(target_path, chmod)

def calculate_file_checksum(filename, hash_function='sha256'):
    hash_functions = {
        'sha256': hashlib.sha256
    }
    hash_function = hash_functions[hash_function]()
    with open(filename, "rb") as input_file:
        for byte_block in iter(lambda: input_file.read(4096), b""):
            hash_function.update(byte_block)

    return hash_function.hexdigest()

def calculate_dict_checksum(dict_object, hash_function='sha256'):
    hash_functions = {
        'sha256': hashlib.sha256
    }
    hash_function = hash_functions[hash_function]()
    json_dump = json.dumps(dict_object, ensure_ascii=False, sort_keys=True)
    hash_function.update(json_dump.encode('utf-8'))

    return hash_function.hexdigest()
