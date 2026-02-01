import logging

import pytest
from nzshm_common.location.coded_location import CodedLocation
from nzshm_common.location.location import LOCATIONS_BY_ID

from toshi_hazard_store import model

log = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def many_rlz_args():
    yield dict(
        TOSHI_ID='FAk3T0sHi1D==',
        vs30s=[250, 500, 1000, 1500],
        imts=['PGA'],
        locs=[CodedLocation(o['latitude'], o['longitude'], 0.001) for o in list(LOCATIONS_BY_ID.values())[:2]],
        rlzs=[x for x in range(5)],
    )


@pytest.fixture(scope='session')
def many_hazagg_args():
    yield dict(
        HAZARD_MODEL_ID='MODEL_THE_FIRST',
        vs30s=[250, 350, 500, 1000, 1500],
        imts=['PGA', 'SA(0.5)'],
        aggs=[model.AggregationEnum.MEAN.value, model.AggregationEnum._10.value],
        locs=[CodedLocation(o['latitude'], o['longitude'], 0.001) for o in list(LOCATIONS_BY_ID.values())],
    )
