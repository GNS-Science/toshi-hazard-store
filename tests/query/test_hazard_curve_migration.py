"""tests to show that the dataset query drop-in replacement for the dynamodb query works OK"""

import json
import pathlib
from unittest import mock

import pytest

from toshi_hazard_store.query import datasets, hazard_query
from toshi_hazard_store.query.dataset_cache import (
    get_dataset,
    get_dataset_vs30,
    get_dataset_vs30_nloc0,
)
from toshi_hazard_store.query.models import AggregatedHazard
from toshi_hazard_store.query.query_strategies import (
    get_hazard_curves_by_vs30,
    get_hazard_curves_by_vs30_nloc0,
    get_hazard_curves_naive,
)

fixture_path = pathlib.Path(__file__).parent.parent / "fixtures" / "query"


@pytest.fixture(scope="module")
def json_hazard():
    fxt = fixture_path / "API_HAZAGG_SMALL.json"
    assert fxt.exists
    yield json.load(open(fxt))


@pytest.fixture(autouse=True)
def clear_dataset_function_caching():
    """Fixture to clear the dataset caches before each test."""
    get_dataset_vs30_nloc0.cache_clear()
    get_dataset_vs30.cache_clear()
    get_dataset.cache_clear()
    yield  # The test runs here


@pytest.fixture()
def hazagg_fixture_fn(json_hazard):

    def fn(hazard_model, imt, nloc_001, agg, vs30):
        curves = json_hazard["data"]["hazard_curves"]["curves"]
        """A test helper function"""
        nloc_0 = hazard_query.downsample_code(nloc_001, 0.1)
        for curve in curves:
            if (
                curve["hazard_model"] == hazard_model
                and curve["imt"] == imt
                and curve["agg"] == agg
                and curve["loc"] == nloc_0
                and curve["vs30"] == vs30
            ):
                yield AggregatedHazard(
                    "NZSHM22",
                    hazard_model,
                    nloc_001,
                    nloc_0,
                    imt,
                    vs30,
                    agg,
                    curve["curve"]["values"],
                ).to_imt_values()
        return None

    yield fn


@pytest.mark.parametrize(
    "query_fn",
    [
        get_hazard_curves_naive,
        get_hazard_curves_by_vs30,
        get_hazard_curves_by_vs30_nloc0,
        datasets.get_hazard_curves,
    ],
)
@pytest.mark.parametrize("locn", ["-41.300~174.800", "-36.900~174.800"])
@pytest.mark.parametrize("vs30", [400, 1500])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["0.005", "mean"])
def test_get_hazard_curves_from_dataset(
    monkeypatch, hazagg_fixture_fn, query_fn, locn, vs30, imt, aggr
):
    """Happy case tests covers all 3 query strategies and the wrapper"""
    dspath = fixture_path / "HAZAGG_SMALL"
    assert dspath.exists()

    from toshi_hazard_store.query import dataset_cache

    monkeypatch.setattr(dataset_cache, "DATASET_AGGR_URI", str(dspath))

    model = "NSHM_v1.0.4"
    expected = next(hazagg_fixture_fn(model, imt, locn, aggr, vs30))
    # assert expected
    print(expected)

    result = query_fn(
        location_codes=[locn], vs30s=[vs30], hazard_model=model, imts=[imt], aggs=[aggr]
    )

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


@pytest.mark.parametrize("bad_locn", ["-48.000~180.000"])
@pytest.mark.parametrize("vs30", [400, 1500])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["0.005", "mean"])
def test_hazard_curve_query_data_missing_for_one_location(
    monkeypatch, hazagg_fixture_fn, bad_locn, vs30, imt, aggr
):
    """Out of bounds location tests covers just `get_hazard_curves_by_vs30_nloc0` query strategy"""
    dspath = fixture_path / "HAZAGG_SMALL"
    assert dspath.exists()

    from toshi_hazard_store.query import dataset_cache

    monkeypatch.setattr(dataset_cache, "DATASET_AGGR_URI", str(dspath))

    model = "NSHM_v1.0.4"
    good_locn = "-41.300~174.800"

    locations = [good_locn] + [bad_locn]

    expected = next(hazagg_fixture_fn(model, imt, good_locn, aggr, vs30))

    result = get_hazard_curves_by_vs30_nloc0(
        location_codes=locations,
        vs30s=[vs30],
        hazard_model=model,
        imts=[imt],
        aggs=[aggr],
    )

    res = next(result)  # one curve is returned

    # the second curve was not ....
    with pytest.raises(RuntimeWarning, match=r".*Failed to open dataset.*"):
        next(result)  # second curve raises an exception

    with pytest.raises(StopIteration):
        next(result)  # no more data

    # Check the returned data is correct
    assert res.hazard_model_id == expected.hazard_model_id
    assert res.imt == expected.imt
    assert res.vs30 == expected.vs30
    assert res.agg == expected.agg
    assert res.nloc_001 == expected.nloc_001


@pytest.mark.parametrize(
    "query_fn",
    [get_hazard_curves_by_vs30, get_hazard_curves_by_vs30_nloc0],
)
@pytest.mark.parametrize("bad_vs30", [401, 155])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["0.005", "mean"])
def test_hazard_curve_query_data_missing_for_vs30(
    monkeypatch, hazagg_fixture_fn, query_fn, bad_vs30, imt, aggr
):
    """Out of bounds (vs30) covers queries using vs30 partioning"""
    dspath = fixture_path / "HAZAGG_SMALL"
    assert dspath.exists()

    from toshi_hazard_store.query import dataset_cache

    monkeypatch.setattr(dataset_cache, "DATASET_AGGR_URI", str(dspath))

    model = "NSHM_v1.0.4"
    good_locn = "-41.300~174.800"
    good_vs30 = 1500
    vs30 = [good_vs30] + [bad_vs30]
    locations = [good_locn]

    expected = next(hazagg_fixture_fn(model, imt, good_locn, aggr, good_vs30))

    result = query_fn(
        location_codes=locations,
        vs30s=vs30,
        hazard_model=model,
        imts=[imt],
        aggs=[aggr],
    )

    res = next(result)  # one curve is returned

    # the second curve was not ....
    with pytest.raises(RuntimeWarning, match=r".*Failed to open dataset.*"):
        next(result)  # second curve raises an exception

    with pytest.raises(StopIteration):
        next(result)  # no more data

    # Check the returned data is correct
    assert res.hazard_model_id == expected.hazard_model_id
    assert res.imt == expected.imt
    assert res.vs30 == expected.vs30
    assert res.agg == expected.agg
    assert res.nloc_001 == expected.nloc_001


def test_hazard_curve_query_default_strategy_is_naive(monkeypatch):

    mocked_qry_fn = mock.Mock(return_value=[])
    monkeypatch.setattr(datasets, "get_hazard_curves_naive", mocked_qry_fn)

    model = "NSHM_v1.0.4"
    good_locn = "-41.300~174.800"
    locations = [good_locn]
    imt = "PGA"
    aggr = "mean"
    vs30 = 400

    result = datasets.get_hazard_curves(
        location_codes=locations,
        vs30s=[vs30],
        hazard_model=model,
        imts=[imt],
        aggs=[aggr],
    )

    with pytest.raises(StopIteration):
        next(result)  # no data

    assert mocked_qry_fn.call_count == 1
    mocked_qry_fn.assert_called_with(
        [good_locn],
        [vs30],
        model,
        [imt],
        [aggr],
    )


@pytest.mark.parametrize(
    "strategy_fn_name",
    [
        ("d1", "get_hazard_curves_by_vs30"),
        ("d2", "get_hazard_curves_by_vs30_nloc0"),
        ("naive", "get_hazard_curves_naive"),
        ("", "get_hazard_curves_naive"),
    ],
)
def test_hazard_curve_query_strategy_calls_correct_query_fn(
    monkeypatch, strategy_fn_name
):

    mocked_qry_fn = mock.Mock(return_value=[])
    monkeypatch.setattr(datasets, strategy_fn_name[1], mocked_qry_fn)

    model = "NSHM_v1.0.4"
    good_locn = "-41.300~174.800"
    locations = [good_locn]
    imt = "PGA"
    aggr = "mean"
    vs30 = 400

    result = datasets.get_hazard_curves(
        location_codes=locations,
        vs30s=[vs30],
        hazard_model=model,
        imts=[imt],
        aggs=[aggr],
        strategy=strategy_fn_name[0],
    )

    with pytest.raises(StopIteration):
        next(result)  # no data

    assert mocked_qry_fn.call_count == 1
    mocked_qry_fn.assert_called_with(
        [good_locn],
        [vs30],
        model,
        [imt],
        [aggr],
    )


@pytest.mark.parametrize("strategy", ["d1", "d2"])
def test_hazard_curve_query_strategy_unmocked(monkeypatch, strategy):

    dspath = fixture_path / "HAZAGG_SMALL"
    assert dspath.exists()

    from toshi_hazard_store.query import dataset_cache

    monkeypatch.setattr(dataset_cache, "DATASET_AGGR_URI", str(dspath))

    model = "NSHM_v1.0.4"
    good_locn = "-41.300~174.800"
    locations = [good_locn]
    imt = "PGA"
    aggr = "mean"
    vs30 = 401

    result = datasets.get_hazard_curves(
        location_codes=locations,
        vs30s=[vs30],
        hazard_model=model,
        imts=[imt],
        aggs=[aggr],
        strategy=strategy,
    )

    # the second curve was not ....
    with pytest.raises(RuntimeWarning, match=r".*Failed to open dataset.*"):
        next(result)  # second curve raises an exception

    with pytest.raises(StopIteration):
        next(result)  # no data
