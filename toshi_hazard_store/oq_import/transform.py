"""Helper functions to export an openquake calculation and save it with toshi-hazard-store."""

from collections import namedtuple
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from toshi_hazard_store.oq_import.h5py_reader import OqHdf5Reader

CustomLocation = namedtuple("CustomLocation", "site_code lon lat")
CustomHazardCurve = namedtuple("CustomHazardCurve", "loc poes")


@dataclass
class Realization:
    source_path: tuple[str]
    gsim_path: tuple[str]
    ordinal: int


def parse_logic_tree_branches(reader: 'OqHdf5Reader') -> tuple[dict[str, str], dict[str, str], list[Realization]]:
    """Parse the hazard logic tree from an OqHdf5Reader.

    This function will return dicts for the source and ground motion branches and a list of realizations
    that relate the source and ground motion branches.

    The source and ground motion branch dicts are keyed by the id of the branch. e.g. "AA" for source branches
    and "gB1" for ground motion branches. The values of the dicts are branch names that can be used by nzhsm_model
    to get the branch registry.

    Realization objects have a source_path, gsim_path, and ordinal. The paths are tuples of branch names (for
    source branches) or branch ids (for ground motion branches).

    Args:
        reader: an OqHdf5Reader for an OpenQuake hdf5

    Returns:
        A tuple of (source_branches, gsim_branches, realizations) where
            source_branches: {str(i): sm_lt_path_str}
            gsim_branches: {branch id: branch name}
            realizations: list[Realizations]
    """
    source_branches = reader.source_branches()
    gsim_branches = reader.gsim_branches()
    realizations = [
        Realization(source_path=r.source_path, gsim_path=r.gsim_path, ordinal=r.ordinal) for r in reader.realizations()
    ]
    return source_branches, gsim_branches, realizations
