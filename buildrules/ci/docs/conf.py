# -*- coding: utf-8 -*-

import sys
import os

extensions = [
    'sphinx.ext.todo',
    'sphinx.ext.ifconfig',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = u'Science Build Environment'
copyright = u'2019, Aalto Science-IT'
author = u'Aalto Science-IT'

import datetime
version = release = ''

language = 'en'

exclude_patterns = ['_build']

default_role = 'any'

pygments_style = 'sphinx'

todo_include_todos = True

html_theme = 'alabaster'

import sphinx_rtd_theme
html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_theme_options = {
    'display_version': False,
    }
# html_context = {'display_github': True,
#                 'github_user': 'AaltoScienceIT',
#                 'github_repo': 'science-build-environment',
#                 'github_version': 'master/',
#                }

def setup(app):
    app.add_stylesheet("custom.css")