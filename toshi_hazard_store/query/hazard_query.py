"""Helpers for querying Hazard Realizations and related dynamodb models.

Provides efficient queries for the models: **HazardAggregation, OpenquakeRealization & ToshiOpenquakeMeta*.*

Functions:

 - **get_hazard_metadata_v3()**  - returns iterator of matching ToshiOpenquakeMeta objects.
 - **get_rlz_curves_v3()**   - returns iterator of matching OpenquakeRealization objects.
 - **get_hazard_curves()**  - returns iterator of HazardAggregation objects.

"""

import logging
from typing import Iterable

from nzshm_common.location.coded_location import CodedLocation

log = logging.getLogger(__name__)


def downsample_code(loc_code, res):
    lt = loc_code.split('~')
    assert len(lt) == 2
    return CodedLocation(lat=float(lt[0]), lon=float(lt[1]), resolution=res).code


def get_hashes(locs: Iterable[str], resolution: float = 0.1):
    hashes = set()
    for loc in locs:
        lt = loc.split('~')
        assert len(lt) == 2
        hashes.add(downsample_code(loc, resolution))
    return sorted(list(hashes))
