import os
import unittest
from moto import mock_dynamodb
import numpy as np

from pathlib import Path
from nzshm_common.location.code_location import CodedLocation

from toshi_hazard_store import model


folder = Path(Path(os.path.realpath(__file__)).parent, 'fixtures', 'disaggregation')
disaggs = np.load(Path(folder, 'deagg_SLT_v8_gmm_v2_FINAL_-39.000~175.930_750_SA(0.5)_86_eps-dist-mag-trt.npy'))
bins = np.load(
    Path(folder, 'bins_SLT_v8_gmm_v2_FINAL_-39.000~175.930_750_SA(0.5)_86_eps-dist-mag-trt.npy'), allow_pickle=True
)


def get_one_disagg_aggregate():
    # lvps = list(map(lambda x: model.LevelValuePairAttribute(lvl=x / 1e3, val=(x / 1e6)), range(1, 51)))
    location = CodedLocation(lat=-41.3, lon=174.78, resolution=0.001)
    return model.DisaggAggregation(
        disaggs=disaggs, bins=bins, agg=model.AggregationEnum.MEAN, imt="PGA", vs30=450, hazard_model_id="HAZ_MODEL_ONE"
    ).set_location(location)


@mock_dynamodb
class PynamoTestDisaggAggregationQuery(unittest.TestCase):
    def setUp(self):

        model.migrate_openquake()
        super(PynamoTestDisaggAggregationQuery, self).setUp()

    def tearDown(self):
        model.drop_openquake()
        return super(PynamoTestDisaggAggregationQuery, self).tearDown()

    def test_attribute_compression(self):
        """Test if compressing the numpy adday is worthwhile."""
        print("Size of the array: ", disaggs.size)
        print("Memory size of one array element in bytes: ", disaggs.itemsize)
        array_size = disaggs.size * disaggs.itemsize
        print("Memory size of numpy array in bytes:", array_size)

        import zlib
        import sys
        import pickle

        comp = zlib.compress(pickle.dumps(disaggs))
        uncomp = pickle.loads(zlib.decompress(comp))

        assert uncomp.all() == disaggs.all()
        self.assertTrue(sys.getsizeof(comp) < array_size / 5)

    def test_model_query_no_condition(self):
        """fetch the single object from tbale and check it's structure OK."""

        dag = get_one_disagg_aggregate()
        dag.save()

        # query on model
        res = list(model.DisaggAggregation.query(dag.partition_key))[0]

        self.assertEqual(res.partition_key, dag.partition_key)
        self.assertEqual(res.sort_key, dag.sort_key)

        # check disaggs attribute
        self.assertEqual(res.disaggs.all(), disaggs.all())

        # check bins attribute

        print(bins)
        print()
        print(res.bins)

        for idx in range(len(bins)):
            print(idx, type(bins[idx]))
            if type(bins[idx]) == list:
                assert res.bins[idx] == bins[idx]
            elif type(bins[idx]) == np.ndarray:
                assert res.bins[idx].all() == bins[idx].all()
            else:
                assert res.bins[idx] == bins[idx]

    def test_model_query_equal_condition(self):

        dag = get_one_disagg_aggregate()
        dag.save()

        # query on model
        res = list(
            model.DisaggAggregation.query(
                dag.partition_key, model.DisaggAggregation.sort_key == '-41.300~174.780:450:PGA:mean:HAZ_MODEL_ONE'
            )
        )[0]
        self.assertEqual(res.partition_key, dag.partition_key)
        self.assertEqual(res.sort_key, dag.sort_key)