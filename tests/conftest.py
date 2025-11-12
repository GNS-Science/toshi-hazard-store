import itertools
import logging

import pytest
from nzshm_common.location.coded_location import CodedLocation
from nzshm_common.location.location import LOCATIONS_BY_ID

from toshi_hazard_store import model

log = logging.getLogger(__name__)


@pytest.fixture
def many_rlz_args():
    yield dict(
        TOSHI_ID='FAk3T0sHi1D==',
        vs30s=[250, 500, 1000, 1500],
        imts=['PGA'],
        locs=[CodedLocation(o['latitude'], o['longitude'], 0.001) for o in list(LOCATIONS_BY_ID.values())[:2]],
        rlzs=[x for x in range(5)],
    )


@pytest.fixture(scope='function')
def build_rlzs_v3_models(many_rlz_args, adapted_rlz_model):
    """New realization handles all the IMT levels."""

    n_lvls = 29

    def model_generator():
        # rlzs = [x for x in range(5)]
        for rlz in many_rlz_args['rlzs']:
            values = []
            for imt, val in enumerate(many_rlz_args['imts']):
                values.append(
                    model.IMTValuesAttribute(
                        imt=val,
                        lvls=[x / 1e3 for x in range(1, n_lvls)],
                        vals=[x / 1e6 for x in range(1, n_lvls)],
                    )
                )
            for loc, vs30 in itertools.product(many_rlz_args["locs"][:5], many_rlz_args["vs30s"]):
                yield model.OpenquakeRealization(
                    values=values,
                    rlz=rlz,
                    vs30=vs30,
                    site_vs30=vs30,
                    hazard_solution_id=many_rlz_args["TOSHI_ID"],
                    source_tags=['TagOne'],
                    source_ids=['Z', 'XX'],
                ).set_location(loc)

    yield model_generator


@pytest.fixture
def many_hazagg_args():
    yield dict(
        HAZARD_MODEL_ID='MODEL_THE_FIRST',
        vs30s=[250, 350, 500, 1000, 1500],
        imts=['PGA', 'SA(0.5)'],
        aggs=[model.AggregationEnum.MEAN.value, model.AggregationEnum._10.value],
        locs=[CodedLocation(o['latitude'], o['longitude'], 0.001) for o in list(LOCATIONS_BY_ID.values())],
    )


@pytest.fixture(scope='function')
def build_hazard_aggregation_models(many_hazagg_args, adapted_hazagg_model):
    def model_generator():
        n_lvls = 29
        lvps = list(map(lambda x: model.LevelValuePairAttribute(lvl=x / 1e3, val=(x / 1e6)), range(1, n_lvls)))
        for loc, vs30, agg in itertools.product(
            many_hazagg_args['locs'][:5], many_hazagg_args['vs30s'], many_hazagg_args['aggs']
        ):
            for imt, val in enumerate(many_hazagg_args['imts']):
                yield model.HazardAggregation(
                    values=lvps,
                    vs30=vs30,
                    agg=agg,
                    imt=val,
                    hazard_model_id=many_hazagg_args['HAZARD_MODEL_ID'],
                ).set_location(loc)

    yield model_generator


@pytest.fixture()
def build_hazagg_models(adapted_hazagg_model, build_hazard_aggregation_models):
    with adapted_hazagg_model.HazardAggregation.batch_write() as batch:
        for item in build_hazard_aggregation_models():
            batch.save(item)
