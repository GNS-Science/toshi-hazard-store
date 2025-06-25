"""tests to show that the dataset query drop-in replacement for the dynamodb query works OK"""

import json
import pathlib

import pytest
from nzshm_common.location import CodedLocation

from toshi_hazard_store.query import datasets

fixture_path = pathlib.Path(__file__).parent.parent / 'fixtures' / 'query'


# @pytest.fixture(autouse=True)
# def set_expected_vs30(monkeypatch):
#     monkeypatch.setattr(nshm_hazard_graphql_api.schema.toshi_hazard.hazard_curves, "DATASET_VS30", [400, 750])


@pytest.fixture()
def hazagg_fixture_fn():
    def fn(model, imt, loc, agg, vs30):
        """Test helper function"""
        fxt = fixture_path / 'HAZAGG_2022_API_JSON' / f"{model}_{imt}_{loc}_{agg}_{vs30}.json"
        assert fxt.exists
        return json.load(open(fxt))

    yield fn


@pytest.fixture()
def dataset_locations():
    yield [
        CodedLocation(-36.87, 174.77, 0.001),
        CodedLocation(-41.3, 174.78, 0.001),
    ]


@pytest.mark.parametrize('query_fn', [datasets.get_hazard_curves_0, datasets.get_hazard_curves_1])
@pytest.mark.parametrize("vs30", [400, 750])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["mean"])
def test_get_hazard_curves_0_dataset(monkeypatch, hazagg_fixture_fn, query_fn, vs30, imt, aggr):
    dspath = fixture_path / 'AGG_THS1.1_DFG'
    assert dspath.exists()

    monkeypatch.setattr(datasets, 'DATASET_AGGR_URI', str(dspath))

    model = "NSHM_v1.0.4"
    locn = "-41.300~174.780"

    expected = hazagg_fixture_fn(model, imt, locn, aggr, vs30)

    result = query_fn(location_codes=[locn], vs30s=[vs30], hazard_model=model, imts=[imt], aggs=[aggr])

    res = next(result)  # only one curve is returned
    print(res)

    assert res.hazard_model_id == expected['data']['hazard_curves']['curves'][0]['hazard_model']
    assert res.imt == expected['data']['hazard_curves']['curves'][0]['imt']
    assert res.vs30 == expected['data']['hazard_curves']['curves'][0]['vs30']
    assert res.agg == expected['data']['hazard_curves']['curves'][0]['agg']
    assert res.nloc_001 == expected['data']['hazard_curves']['curves'][0]['loc']

    # assert res.values[-1].lvl == expected['data']['hazard_curves']['curves'][0]['curve']['levels'][-1]

    # Check values and levels from original DynamoDB table vs new aggregate pyarrow dataset.
    # note the value differences here (< 5e-9) are down to minor changes in THP processing.
    for idx, value in enumerate(res.values):

        exp_value = expected['data']['hazard_curves']['curves'][0]['curve']['values'][idx]
        exp_level = expected['data']['hazard_curves']['curves'][0]['curve']['levels'][idx]

        print(
            f"testing idx: {idx} level: {value.lvl} res_value: {value.val}"
            f" expected_value: {exp_value}. diff: {exp_value - value.val}"
        )
        assert value.val == pytest.approx(exp_value, abs=3e-8)
        assert value.lvl == exp_level
