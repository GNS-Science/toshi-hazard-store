"""
Look for evidence of any missing aggregations across

 - Aggregate dataset
 - RAW aggregates (partitioned by vs30, imt, nloc_001)
 - all 18 VS30
 - all types of locaion (grid, NZ, SWRG)
"""

import logging
import random

from nzshm_common.location import get_locations
from pyarrow import fs

from toshi_hazard_store.query import datasets

log = logging.getLogger(__name__)

nz1_grid = [loc.code for loc in get_locations(['NZ_0_1_NB_1_1'])]
city_locs = [loc.code for loc in get_locations(['NZ'])]
srwg_locs = [loc.code for loc in get_locations(['SRWG214'])]

vs30s = [400, 1000, 1500]
vs30s += [375, 450, 500, 525, 600, 750, 900]
vs30s += [150, 175, 200, 225, 250, 275, 300, 350]


def check(get_locations_fn, test_label="NZ cities"):
    """Check that the correct number of curves are returned"""

    print(f'check {test_label}')
    model = "NSHM_v1.0.4"
    imt = "PGA"
    aggr = "mean"

    for vs30 in vs30s:
        found_locs = []
        print(f"checking vs30: {vs30}")
        locations = get_locations_fn()

        for loc in locations:
            res = list(
                datasets.get_hazard_curves(
                    location_codes=[loc], vs30s=[vs30], hazard_model=model, imts=[imt], aggs=[aggr], strategy='d1'
                )
            )

            if len(res) == 1:
                found_locs.append(loc)
            elif len(res) == 0:
                log.info(f"missing data {vs30}, {loc}")
            else:
                assert 0, "only one curve is allowed"

        if set(found_locs) == set(locations):
            print(f"{test_label} OK for vs30: {vs30}")
        else:
            print(f"expected data for locations: {locations}")
            print(f"Missing {test_label}for vs30 {vs30}: {set(locations).difference(set(found_locs))}")


if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING)

    # # GRID test
    check(lambda: random.sample(nz1_grid, 10), test_label="1O of NZ grid")

    # NZ cities test
    check(lambda: random.sample(city_locs, 5))

    # SRWG test
    check(lambda: random.sample(srwg_locs, 5), test_label="10 of SRWG214")
