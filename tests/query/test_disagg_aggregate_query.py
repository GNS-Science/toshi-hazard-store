"""Tests for get_disagg_aggregates query function and strategies."""

import math
from unittest import mock

import pytest

from toshi_hazard_store import query
from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.hazard_models_pydantic import DisaggregationAggregate
from toshi_hazard_store.model.pyarrow import pyarrow_dataset, pyarrow_disagg_aggr_dataset
from toshi_hazard_store.model.revision_4.extract_disagg_hdf5 import _bins_digest_from_dict
from toshi_hazard_store.query import datasets as datasets_mod
from toshi_hazard_store.query.dataset_cache import (
    get_disagg_aggr_dataset,
    get_disagg_aggr_dataset_digest_vs30,
    get_disagg_aggr_dataset_digest_vs30_nloc0,
)
from toshi_hazard_store.query.query_strategies import (
    get_disagg_aggregates_by_digest_vs30,
    get_disagg_aggregates_by_digest_vs30_nloc0,
    get_disagg_aggregates_naive,
)

_BINS = {
    "mag": ["5.5", "6.5", "7.5"],
    "dist": ["10.0", "50.0", "100.0", "200.0"],
    "eps": ["-1.0", "0.0", "1.0"],
}
_EXPECTED_SHAPE = tuple(len(v) for v in _BINS.values())
_N_VALUES = math.prod(_EXPECTED_SHAPE)


@pytest.fixture(autouse=True)
def clear_disagg_dataset_caches():
    """Clear disagg dataset caches before each test."""
    get_disagg_aggr_dataset.cache_clear()
    get_disagg_aggr_dataset_digest_vs30.cache_clear()
    get_disagg_aggr_dataset_digest_vs30_nloc0.cache_clear()
    yield


@pytest.fixture(scope="module")
def disagg_aggr_dataset(tmp_path_factory):
    """Build a small disagg-aggregate parquet dataset partitioned by bins_digest/vs30/nloc_0."""
    out = tmp_path_factory.mktemp("DISAGG_AGGR_SMALL")
    digest = _bins_digest_from_dict(_BINS)

    models = [
        DisaggregationAggregate(
            compatible_calc_id="NZSHM22",
            hazard_model_id="NSHM_v1.0.4",
            nloc_001=loc,
            nloc_0=query.downsample_code(loc, 1.0),
            vs30=vs30,
            imt=imt,
            target_aggr=target_aggr,
            probability=ProbabilityEnum._10_PCT_IN_50YRS,
            imtl=0.1,
            aggr=aggr,
            bins_digest=digest,
            disagg_bins=_BINS,
            disagg_values=[float(j) for j in range(_N_VALUES)],
        )
        for loc in ("-41.300~174.800", "-36.900~174.800")
        for vs30 in (400, 1500)
        for imt in ("PGA", "SA(0.5)")
        for target_aggr in ("mean",)
        for aggr in ("mean", "0.005")
    ]

    base_dir, fs_ = pyarrow_dataset.configure_output(str(out))
    pyarrow_disagg_aggr_dataset.append_models_to_dataset(
        models=iter(models),
        base_dir=base_dir,
        filesystem=fs_,
        partitioning=["bins_digest", "vs30", "nloc_0"],
    )

    # Fail loudly if the writer PR uses a different partition layout.
    assert (out / f"bins_digest={digest}" / "vs30=400").exists(), (
        f"Expected partition layout bins_digest/vs30/nloc_0 not found under {out}. "
        "Check that the disagg writer uses partitioning=['bins_digest', 'vs30', 'nloc_0']."
    )

    return out, digest


@pytest.mark.parametrize(
    "query_fn",
    [
        get_disagg_aggregates_naive,
        get_disagg_aggregates_by_digest_vs30,
        get_disagg_aggregates_by_digest_vs30_nloc0,
        query.get_disagg_aggregates,
    ],
)
@pytest.mark.parametrize("locn", ["-41.300~174.800", "-36.900~174.800"])
@pytest.mark.parametrize("vs30", [400, 1500])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["mean", "0.005"])
def test_get_disagg_aggregates_from_dataset(disagg_aggr_dataset, query_fn, locn, vs30, imt, aggr):
    """Happy-path: all 3 strategies and the wrapper return the correct disagg aggregate."""
    dspath, digest = disagg_aggr_dataset

    model = "NSHM_v1.0.4"
    target_aggr = "mean"
    prob = ProbabilityEnum._10_PCT_IN_50YRS

    is_strategy = query_fn in (
        get_disagg_aggregates_naive,
        get_disagg_aggregates_by_digest_vs30,
        get_disagg_aggregates_by_digest_vs30_nloc0,
    )

    if is_strategy:
        result = query_fn(
            location_codes=[locn],
            vs30s=[vs30],
            hazard_model=model,
            imts=[imt],
            aggs=[aggr],
            target_aggrs=[target_aggr],
            probabilities=[prob],
            bins_digest=digest,
            dataset_uri=str(dspath),
        )
    else:
        result = query_fn(
            location_codes=[locn],
            vs30s=[vs30],
            hazard_model=model,
            imts=[imt],
            aggs=[aggr],
            target_aggrs=[target_aggr],
            probabilities=[prob],
            disagg_bins=_BINS,
            dataset_uri=str(dspath),
        )

    res = next(result)

    assert res.hazard_model_id == model
    assert res.imt == imt
    assert res.vs30 == vs30
    assert res.aggr == aggr
    assert res.target_aggr == target_aggr
    assert res.probability == prob
    assert res.bins_digest == digest
    assert res.nloc_001 == locn
    assert len(res.disagg_values) == _N_VALUES
    assert res.to_ndarray().shape == _EXPECTED_SHAPE


@pytest.mark.parametrize("bad_locn", ["-48.000~180.000"])
@pytest.mark.parametrize("vs30", [400, 1500])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["mean", "0.005"])
def test_disagg_query_data_missing_for_one_location(monkeypatch, disagg_aggr_dataset, bad_locn, vs30, imt, aggr):
    """d2 strategy raises deferred RuntimeWarning when a location partition is absent."""
    dspath, digest = disagg_aggr_dataset
    monkeypatch.setattr("toshi_hazard_store.query.dataset_cache.DATASET_DISAGG_AGGR_URI", str(dspath))

    good_locn = "-41.300~174.800"

    result = get_disagg_aggregates_by_digest_vs30_nloc0(
        location_codes=[good_locn, bad_locn],
        vs30s=[vs30],
        hazard_model="NSHM_v1.0.4",
        imts=[imt],
        aggs=[aggr],
        target_aggrs=["mean"],
        probabilities=[ProbabilityEnum._10_PCT_IN_50YRS],
        bins_digest=digest,
    )

    res = next(result)
    assert res.hazard_model_id == "NSHM_v1.0.4"

    with pytest.raises(RuntimeWarning, match=r".*Failed to open dataset.*"):
        next(result)

    with pytest.raises(StopIteration):
        next(result)


@pytest.mark.parametrize(
    "query_fn",
    [get_disagg_aggregates_by_digest_vs30, get_disagg_aggregates_by_digest_vs30_nloc0],
)
@pytest.mark.parametrize("bad_vs30", [401, 155])
@pytest.mark.parametrize("imt", ["PGA", "SA(0.5)"])
@pytest.mark.parametrize("aggr", ["mean", "0.005"])
def test_disagg_query_data_missing_for_vs30(monkeypatch, disagg_aggr_dataset, query_fn, bad_vs30, imt, aggr):
    """d1/d2 strategies raise deferred RuntimeWarning when a vs30 partition is absent."""
    dspath, digest = disagg_aggr_dataset
    monkeypatch.setattr("toshi_hazard_store.query.dataset_cache.DATASET_DISAGG_AGGR_URI", str(dspath))

    result = query_fn(
        location_codes=["-41.300~174.800"],
        vs30s=[1500, bad_vs30],
        hazard_model="NSHM_v1.0.4",
        imts=[imt],
        aggs=[aggr],
        target_aggrs=["mean"],
        probabilities=[ProbabilityEnum._10_PCT_IN_50YRS],
        bins_digest=digest,
    )

    res = next(result)
    assert res.hazard_model_id == "NSHM_v1.0.4"

    with pytest.raises(RuntimeWarning, match=r".*Failed to open dataset.*"):
        next(result)

    with pytest.raises(StopIteration):
        next(result)


def test_disagg_query_bad_bins_digest_naive_yields_nothing(monkeypatch, disagg_aggr_dataset):
    """Naive strategy with a wrong bins_digest column-filters to zero rows."""
    dspath, _ = disagg_aggr_dataset
    monkeypatch.setattr("toshi_hazard_store.query.dataset_cache.DATASET_DISAGG_AGGR_URI", str(dspath))

    result = list(
        get_disagg_aggregates_naive(
            location_codes=["-41.300~174.800"],
            vs30s=[400],
            hazard_model="NSHM_v1.0.4",
            imts=["PGA"],
            aggs=["mean"],
            target_aggrs=["mean"],
            probabilities=[ProbabilityEnum._10_PCT_IN_50YRS],
            bins_digest="0000000000000000",
        )
    )
    assert result == []


@pytest.mark.parametrize(
    "query_fn",
    [get_disagg_aggregates_by_digest_vs30, get_disagg_aggregates_by_digest_vs30_nloc0],
)
def test_disagg_query_bad_bins_digest_d1_d2_raises_warning(monkeypatch, disagg_aggr_dataset, query_fn):
    """d1/d2 strategies raise deferred RuntimeWarning when the bins_digest partition is absent."""
    dspath, _ = disagg_aggr_dataset
    monkeypatch.setattr("toshi_hazard_store.query.dataset_cache.DATASET_DISAGG_AGGR_URI", str(dspath))

    result = query_fn(
        location_codes=["-41.300~174.800"],
        vs30s=[400],
        hazard_model="NSHM_v1.0.4",
        imts=["PGA"],
        aggs=["mean"],
        target_aggrs=["mean"],
        probabilities=[ProbabilityEnum._10_PCT_IN_50YRS],
        bins_digest="0000000000000000",
    )

    with pytest.raises(RuntimeWarning, match=r".*Failed to open dataset.*"):
        next(result)

    with pytest.raises(StopIteration):
        next(result)


def test_disagg_query_default_strategy_is_naive(monkeypatch):
    """Wrapper uses the naive strategy when no strategy is specified."""
    mocked_qry_fn = mock.Mock(return_value=[])
    monkeypatch.setattr("toshi_hazard_store.query.datasets.get_disagg_aggregates_naive", mocked_qry_fn)

    model = "NSHM_v1.0.4"
    locn = "-41.300~174.800"
    prob = ProbabilityEnum._10_PCT_IN_50YRS
    digest = _bins_digest_from_dict(_BINS)

    result = query.get_disagg_aggregates(
        location_codes=[locn],
        vs30s=[400],
        hazard_model=model,
        imts=["PGA"],
        aggs=["mean"],
        target_aggrs=["mean"],
        probabilities=[prob],
        disagg_bins=_BINS,
    )

    with pytest.raises(StopIteration):
        next(result)

    assert mocked_qry_fn.call_count == 1
    mocked_qry_fn.assert_called_with([locn], [400], model, ["PGA"], ["mean"], ["mean"], [prob], digest, None)


@pytest.mark.parametrize(
    "strategy_fn_name",
    [
        ("d1", "get_disagg_aggregates_by_digest_vs30"),
        ("d2", "get_disagg_aggregates_by_digest_vs30_nloc0"),
        ("naive", "get_disagg_aggregates_naive"),
        ("", "get_disagg_aggregates_naive"),
    ],
)
def test_disagg_query_strategy_calls_correct_query_fn(monkeypatch, strategy_fn_name):
    """Wrapper dispatches to the correct strategy function."""
    mocked_qry_fn = mock.Mock(return_value=[])
    monkeypatch.setattr(datasets_mod, strategy_fn_name[1], mocked_qry_fn)

    model = "NSHM_v1.0.4"
    locn = "-41.300~174.800"
    prob = ProbabilityEnum._10_PCT_IN_50YRS
    digest = _bins_digest_from_dict(_BINS)

    result = query.get_disagg_aggregates(
        location_codes=[locn],
        vs30s=[400],
        hazard_model=model,
        imts=["PGA"],
        aggs=["mean"],
        target_aggrs=["mean"],
        probabilities=[prob],
        disagg_bins=_BINS,
        strategy=strategy_fn_name[0],
    )

    with pytest.raises(StopIteration):
        next(result)

    assert mocked_qry_fn.call_count == 1
    mocked_qry_fn.assert_called_with([locn], [400], model, ["PGA"], ["mean"], ["mean"], [prob], digest, None)


@pytest.mark.parametrize("strategy", ["d1", "d2"])
def test_disagg_query_strategy_unmocked(monkeypatch, disagg_aggr_dataset, strategy):
    """d1 and d2 strategies raise RuntimeWarning when vs30 partition is absent."""
    dspath, _ = disagg_aggr_dataset
    monkeypatch.setattr("toshi_hazard_store.query.dataset_cache.DATASET_DISAGG_AGGR_URI", str(dspath))

    result = query.get_disagg_aggregates(
        location_codes=["-41.300~174.800"],
        vs30s=[401],  # not in dataset
        hazard_model="NSHM_v1.0.4",
        imts=["PGA"],
        aggs=["mean"],
        target_aggrs=["mean"],
        probabilities=[ProbabilityEnum._10_PCT_IN_50YRS],
        disagg_bins=_BINS,
        strategy=strategy,
    )

    with pytest.raises(RuntimeWarning, match=r".*Failed to open dataset.*"):
        next(result)

    with pytest.raises(StopIteration):
        next(result)
