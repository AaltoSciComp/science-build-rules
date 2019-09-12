# -*- coding: utf-8 -*-
"""buildrules contains various build setups.
"""
from buildrules.anaconda import AnacondaBuilder
from buildrules.ci import CIBuilder
from buildrules.spack import SpackBuilder


BUILDERS = {
    'anaconda': AnacondaBuilder,
    'ci': CIBuilder,
    'spack': SpackBuilder,
}
