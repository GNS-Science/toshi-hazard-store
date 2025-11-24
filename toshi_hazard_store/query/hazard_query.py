"""Helpers for location queries using CodedLocation from nzshm-common.

TODO: these coded-location string functions should move to nzshm-common.
"""

import logging
from typing import Iterable

from nzshm_common.location.coded_location import CodedLocation

log = logging.getLogger(__name__)


def downsample_code(loc_code, res) -> str:
    """Get a CodedLocation.code at the chosen resolution from the given location code.

    Args:
        loc_code (str): The location code in format 'latitude~longitude'.
        resolution (int): Resolution in grid degrees to downsample to.

    Returns:
        str: The downsampled location code.

    Examples:
        >>> downsample_code('37.7749~-122.4194', 0.1)
        '37.8~-122.4'
    """
    lt = loc_code.split('~')
    assert len(lt) == 2
    return CodedLocation(lat=float(lt[0]), lon=float(lt[1]), resolution=res).code


def get_hashes(locs: Iterable[str], resolution: float = 0.1) -> Iterable[str]:
    """Compute a set of hashes for the given locations at the specified resolution.

    Args:
        locs (Iterable[str]): A collection of location codes in the format 'latitude~longitude'.
        resolution (float, optional): The resolution to compute hashes at (in grid degrees). Defaults to 0.1.

    Returns:
        list: A sorted list of unique location codes, downsampled to the specified resolution.
    """
    hashes = set()
    for loc in locs:
        lt = loc.split('~')
        assert len(lt) == 2
        hashes.add(downsample_code(loc, resolution))
    return sorted(list(hashes))
