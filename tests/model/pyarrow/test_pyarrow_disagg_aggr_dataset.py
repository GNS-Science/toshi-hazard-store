import math

import pyarrow.dataset as ds
import pytest

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.hazard_models_pydantic import DisaggregationAggregate
from toshi_hazard_store.model.pyarrow import (
    pyarrow_dataset,
    pyarrow_disagg_aggr_dataset,
)
from toshi_hazard_store.model.pyarrow.disagg_reshape import reshape_disagg_values

_BINS = {
    "mag": ["5.5", "6.5", "7.5"],
    "dist": ["10.0", "50.0", "100.0", "200.0"],
    "eps": ["-1.0", "0.0", "1.0"],
}
_EXPECTED_SHAPE = tuple([len(element) for element in _BINS.values()])
_N_VALUES = math.prod(_EXPECTED_SHAPE)


@pytest.fixture
def disagg_aggregate_models():
    def _models(n=10):
        for i in range(n):
            yield DisaggregationAggregate(
                compatible_calc_id="NZSHM22",
                hazard_model_id="NSHM_v1.0.4",
                nloc_001="-38.330~175.550",
                nloc_0="-38.0~175.0",
                imt="PGA",
                vs30=400,
                target_aggr="mean",
                probability=ProbabilityEnum._10_PCT_IN_50YRS,
                imtl=0.1,
                aggr="mean",
                bins_digest="abc123def456",
                disagg_bins=_BINS,
                disagg_values=[float(j) for j in range(_N_VALUES)],
            )

    return _models()


def test_serialise_disagg_aggregate(tmp_path, disagg_aggregate_models):
    output_folder = tmp_path / "ds_disagg_aggr"

    partitioning = ['vs30', 'nloc_0']
    base_dir, filesystem = pyarrow_dataset.configure_output(str(output_folder))
    pyarrow_disagg_aggr_dataset.append_models_to_dataset(
        models=disagg_aggregate_models, base_dir=base_dir, filesystem=filesystem, partitioning=partitioning
    )

    schema = DisaggregationAggregate.pyarrow_schema()
    dataset = ds.dataset(output_folder, format='parquet', partitioning='hive', schema=schema)
    table = dataset.to_table()
    rows = table.to_pylist()

    assert len(rows) == 10
    arr = reshape_disagg_values(rows[0]["disagg_values"], rows[0]["disagg_bins"])
    assert arr.shape == _EXPECTED_SHAPE
