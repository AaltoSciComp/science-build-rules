# -*- coding: utf-8 -*-
"""buildrules contains various build setups.
"""
from buildrules.spack import SpackBuilder
from buildrules.ci import CIBuilder


BUILDERS = {
    'spack': SpackBuilder,
    'ci': CIBuilder
}
