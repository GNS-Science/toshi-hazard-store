"""Helper functions to export an openquake calculation and save it with toshi-hazard-store.

Courtesy of Anne Hulsey
"""

from collections import namedtuple
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openquake.calculators.extract import Extractor

CustomLocation = namedtuple("CustomLocation", "site_code lon lat")
CustomHazardCurve = namedtuple("CustomHazardCurve", "loc poes")


@dataclass
class Realization:
    source_path: tuple[str]
    gsim_path: tuple[str]
    ordinal: int


def parse_logic_tree_branches(extractor: 'Extractor') -> tuple[dict[str, str], dict[str, str], list[Realization]]:

    full_lt = extractor.get('full_lt')
    source_model_lt = full_lt.source_model_lt
    gslt = full_lt.gsim_lt

    # we don't use the ID, but keeping it as a dict key for symmetry with gsims
    source_branches = {v.id: k for k, v in source_model_lt.branches.items()}

    gsim_branches = {b.id: str(b.gsim) for b in gslt.branches}

    realizations = [
        Realization(source_path=rlz.sm_lt_path, gsim_path=rlz.gsim_lt_path, ordinal=rlz.ordinal)
        for rlz in full_lt.get_realizations()
    ]

    return source_branches, gsim_branches, realizations
