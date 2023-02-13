import itertools
import unittest
import os
import numpy as np
from pathlib import Path
from moto import mock_dynamodb
from nzshm_common.location.code_location import CodedLocation
from nzshm_common.location.location import LOCATIONS_BY_ID

from toshi_hazard_store import model, query

HAZARD_MODEL_ID = 'MODEL_THE_FIRST'
vs30s = [250] #, 350]
imts = ['PGA'] #, 'SA(0.5)']
hazard_aggs = [model.AggregationEnum.MEAN.value] #, model.AggregationEnum._10.value]
disagg_aggs = [model.AggregationEnum.MEAN.value]

locs = [CodedLocation(o['latitude'], o['longitude'], 0.001) for o in LOCATIONS_BY_ID.values()]


folder = Path(Path(os.path.realpath(__file__)).parent, 'fixtures', 'disaggregation')
disaggs = np.ndarray(4,float) #np.load(Path(folder, 'deagg_SLT_v8_gmm_v2_FINAL_-39.000~175.930_750_SA(0.5)_86_eps-dist-mag-trt.npy'))
bins = np.load(
    Path(folder, 'bins_SLT_v8_gmm_v2_FINAL_-39.000~175.930_750_SA(0.5)_86_eps-dist-mag-trt.npy'), allow_pickle=True
)
shaking_level = 0.1

def build_disagg_aggregation_models():
    for (loc, vs30, imt, hazard_agg, disagg_agg) in itertools.product(locs[:1], vs30s, imts, hazard_aggs, disagg_aggs):
        # for imt, val in enumerate(imts):
        yield model.DisaggAggregationExceedance.new_model(
            location=loc,
            disaggs=disaggs,
            bins=bins,
            vs30=vs30,
            hazard_agg=hazard_agg,
            disagg_agg=disagg_agg,
            probability=model.ProbabilityEnum._10_PCT_IN_50YRS,
            shaking_level=shaking_level,
            imt=imt,
            hazard_model_id=HAZARD_MODEL_ID,
            )

@mock_dynamodb
class QueryDisaggAggregationsTest(unittest.TestCase):
    def setUp(self):
        model.migrate()
        with model.DisaggAggregationExceedance.batch_write() as batch:
            for item in build_disagg_aggregation_models():
                batch.save(item)
        super(QueryDisaggAggregationsTest, self).setUp()

    def tearDown(self):
        model.drop_tables()
        return super(QueryDisaggAggregationsTest, self).tearDown()

    def test_query_single_valid_hazard_aggr(self):
        qlocs = [loc.downsample(0.001).code for loc in locs[:1]]

        res =  query.get_one_disagg_aggregation(
            qlocs[0],
            vs30s[0], imts[0],
            model.AggregationEnum.MEAN, model.AggregationEnum.MEAN,
            model.ProbabilityEnum._10_PCT_IN_50YRS,
            HAZARD_MODEL_ID )
        print(res)

        assert res.nloc_001 == qlocs[0]
        assert res.disagg_agg == 'mean'
        assert res.probability == model.ProbabilityEnum._10_PCT_IN_50YRS
        assert res.hazard_model_id == HAZARD_MODEL_ID

    def test_query_single_missing_hazard_aggr(self):
        qlocs = [loc.downsample(0.001).code for loc in locs[:1]]

        res =  query.get_one_disagg_aggregation(
            qlocs[0],
            vs30s[0], imts[0],
            model.AggregationEnum.MEAN, model.AggregationEnum.MEAN,
            model.ProbabilityEnum._2_PCT_IN_50YRS,
            HAZARD_MODEL_ID )
        print(res)
        assert res == None

    @unittest.skip('WIP')
    def test_query_many_valid_hazard_aggr(self):
        qlocs = [loc.downsample(0.001).code for loc in locs[:1]]

        res =  query.get_one_disagg_aggregation(
            qlocs[0],
            vs30s[0],
            imts[0],
            model.AggregationEnum.MEAN,
            model.AggregationEnum.MEAN,
            model.ProbabilityEnum._10_PCT_IN_50YRS,
            HAZARD_MODEL_ID )
        print(res)

        # print(res.partition_key, res.sort_key)
        res =  list(
            query.get_disagg_aggregates(
                qlocs,
                [vs30s[0]],
                [imts[0]],
                [model.AggregationEnum.MEAN],
                [model.AggregationEnum.MEAN],
                [model.ProbabilityEnum._10_PCT_IN_50YRS],
                [HAZARD_MODEL_ID] )
            )
        print(res)
        assert '-36.870~174.770:250:PGA:mean:mean:_10_PCT_IN_50YRS:MODEL_THE_FIRST' >= '-36.870~174.770:250:PGA:mean:mean:_10_PCT_IN_50YRS:MODEL_THE_FIRST'
        # assert 0
        assert len(res) == 1




