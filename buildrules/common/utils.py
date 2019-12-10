# -*- coding: utf-8 -*-
"""Utils contains various useful utilities for builders.
"""
import re
import yaml

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
