# -*- coding: utf-8 -*-
"""buildrules contains various build setups.
"""
from buildrules.anaconda import AnacondaBuilder
from buildrules.ci import CIBuilder
from buildrules.spack import SpackBuilder
from buildrules.singularity import SingularityBuilder


BUILDERS = {
    'anaconda': AnacondaBuilder,
    'ci': CIBuilder,
    'spack': SpackBuilder,
    'singularity': SingularityBuilder
}
