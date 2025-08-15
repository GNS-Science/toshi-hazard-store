"""Helper functions to export an openquake calculation and save it with toshi-hazard-store.

Courtesy of Anne Hulsey
"""

import re
from collections import namedtuple

import numpy as np
import pandas as pd

CustomLocation = namedtuple("CustomLocation", "site_code lon lat")
CustomHazardCurve = namedtuple("CustomHazardCurve", "loc poes")


def parse_logic_tree_branches(extractor):

    full_lt = extractor.get('full_lt')
    source_model_lt = full_lt.source_model_lt
    gslt = full_lt.gsim_lt

    # we don't use the ID, but keeping it as a dict key for symmetry with gsims
    source_branches = {v.id: k for k, v in source_model_lt.branches.items()}

    # NOTE: could be named tuple or dataclass
    gsim_branches = {b.id: str(b.gsim) for b in gslt.branches}

    # NOTE: could be a named tuple or a dataclass
    realizations = [
        {'source_path': rlz.sm_lt_path, 'gsim_path': rlz.gsim_lt_path, 'ordinal': rlz.ordinal}
        for rlz in full_lt.get_realizations()
    ]

    return source_branches, gsim_branches, realizations
