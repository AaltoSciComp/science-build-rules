# -*- coding: utf-8 -*-
"""buildrules contains various build setups.
"""
from buildrules.spack import SpackBuilder


BUILDERS = {
    'spack': SpackBuilder
}
