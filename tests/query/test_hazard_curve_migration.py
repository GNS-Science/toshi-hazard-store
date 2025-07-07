"""tests to show that the dataset query drop-in replacement for the dynamodb query works OK"""

import json
import pathlib

import pytest

from toshi_hazard_store.query import datasets, hazard_query

fixture_path = pathlib.Path(__file__).parent.parent / 'fixtures' / 'query'


@pytest.fixture(scope='module')
def json_hazard():
    fxt = fixture_path / 'API_HAZAGG_SMALL.json'
    assert fxt.exists
    yield json.load(open(fxt))


@pytest.fixture()
def hazagg_fixture_fn(json_hazard):

    def fn(hazard_model, imt, nloc_001, agg, vs30):
        curves = json_hazard['data']['hazard_curves']['curves']
        """A test helper function"""
        nloc_0 = hazard_query.downsample_code(nloc_001, 0.1)
        for curve in curves:
            if (
                curve['hazard_model'] == hazard_model
                and curve['imt'] == imt
                and curve['agg'] == agg
                and curve['loc'] == nloc_0
                and curve['vs30'] == vs30
            ):
                return datasets.AggregatedHazard(
                    'NZSHM22', hazard_model, nloc_001, nloc_0, imt, vs30, agg, curve['curve']['values']
                ).to_imt_values()
        return None

    yield fn


@pytest.mark.parametrize(
    'query_fn',
    [datasets.get_hazard_curves_naive, datasets.get_hazard_curves_by_vs30, datasets.get_hazard_curves_by_vs30_nloc0],
)
@pytest.mark.parametrize("locn", ["-41.300~174.800", "-36.900~174.800"])
@pytest.mark.parametrize("vs30", [400, 1500])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["0.005", "mean"])
def test_get_hazard_curves_0_dataset(monkeypatch, hazagg_fixture_fn, query_fn, locn, vs30, imt, aggr):
    dspath = fixture_path / 'HAZAGG_SMALL'
    assert dspath.exists()

    monkeypatch.setattr(datasets, 'DATASET_AGGR_URI', str(dspath))

    model = "NSHM_v1.0.4"
    expected = hazagg_fixture_fn(model, imt, locn, aggr, vs30)
    # assert expected
    print(expected)

    result = query_fn(location_codes=[locn], vs30s=[vs30], hazard_model=model, imts=[imt], aggs=[aggr])

    res = next(result)  # only one curve is returned

    assert res.hazard_model_id == expected.hazard_model_id
    assert res.imt == expected.imt
    assert res.vs30 == expected.vs30
    assert res.agg == expected.agg
    assert res.nloc_001 == expected.nloc_001

    # Check values and levels from original DynamoDB table vs new aggregate pyarrow dataset.
    # note the value differences here (< 5e-9) are down to minor changes in THP processing.
    for idx, value in enumerate(res.values):

        exp_value = expected.values[idx].val
        exp_level = expected.values[idx].lvl

        print(
            f"testing idx: {idx} level: {value.lvl} res_value: {value.val}"
            f" expected_value: {exp_value}. diff: {exp_value - value.val}"
        )
        assert value.val == pytest.approx(exp_value, abs=7e5 - 8)
        assert value.lvl == exp_level
