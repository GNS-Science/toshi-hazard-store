"""Helper functions to export an openquake calculation and save it with toshi-hazard-store."""

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
    """Parse the hazard logic tree from an OpenQuake Extractor.

    This function will return dicts for the source and ground motion branches and a list of realizations
    that relate the source and ground motion branches.

    The source and ground motion branch dicts are keyed by the id of the branch. e.g. "AA" for source branches
    and "gB1" for ground motion branches. The values of the dicts are branch names that can be used by nzhsm_model
    to get the branch registry.

    Realization objects have a source_path, gsim_path, and ordinal. The paths are tuples of branch names (for
    source branches) or branch ids (for ground motion branches).

    Args:
        extractor: the OpenQuake Extractor for an OpenQuake hdf5

    Returns:
        A tuple of (source_branches, gsim_branches, realizations) where
            source_branches: {branch id:branch name}
            gsim_branches: {branch id: branch name}
            realizations: list[Realizations]
    """

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
