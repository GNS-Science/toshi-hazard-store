# Disaggregation

These models represent aggregated disaggregation arrays derived from OpenQuake PSHA engine outputs.

## Disaggregation Aggregate

The core model for aggregated disaggregation data, stored as PyArrow parquet datasets.

::: toshi_hazard_store.model.hazard_models_pydantic.DisaggregationAggregate
    options:
      show_source: true
      members: false
      attributes: true

## PyArrow Schema

The `DisaggregationAggregate` model can be converted to a PyArrow schema for dataset I/O:

```python
from toshi_hazard_store.model.hazard_models_pydantic import DisaggregationAggregate
schema = DisaggregationAggregate.pyarrow_schema()
```

The schema includes:

- `compatible_calc_id` (string) - Compatible calculation identifier
- `hazard_model_id` (string) - Model identifier (e.g., "NSHM_v1.0.4")
- `bins_digest` (string) - sha256[:16] compatibility key over sorted axes + bin centres
- `nloc_001` (string) - Location to 3 decimal places (e.g., "-41.300~174.800")
- `nloc_0` (string) - Location to 0 decimal places (e.g., "-41.0~174.0") for partitioning
- `vs30` (int32) - VS30 value
- `imt` (string) - Intensity measure type (e.g., "PGA", "SA(1.0)")
- `target_aggr` (string) - Hazard-curve aggregation the disagg was conditioned on (e.g., "mean")
- `probability` (string) - Return-period probability as a `ProbabilityEnum` name (e.g., "_10_PCT_IN_50YRS")
- `imtl` (float) - IML at which the disagg was computed
- `aggr` (string) - Aggregation type across realisations (e.g., "mean", "0.1")
- `disagg_bins` (map of string → list of string) - Ordered map of axis name to bin-centre strings; key order defines the axis order of `disagg_values`
- `disagg_values` (list of float32) - Flattened C-order disaggregation array over `disagg_bins` axes


## Dataset Partitioning

Disaggregation aggregate datasets use Hive-style partitioning on `bins_digest / vs30 / nloc_0`:

```
<dataset_root>/
├── bins_digest=6028db096c3a9e62/
│   ├── vs30=400/
│   │   └── nloc_0=-41.0~174.0/
│   │       └── <uuid>-part-0.parquet
│   └── vs30=1500/
│       └── nloc_0=-41.0~174.0/
│           └── <uuid>-part-0.parquet
```

The `bins_digest` partition groups rows with identical bin topology, enabling efficient filtering when querying a specific disaggregation configuration. Use the `d2` query strategy for large datasets to exploit all three partition levels. The `bins_digest` can be obtained from the `disagg_bins` with `toshi_hazard_store.model.revision_4.extract_disagg_hdf5.compute_bins_digest`.

Note that this partitioning is not enforced by `append_models_to_dataset`, it is left to the user to dictate the partitioning either at write time or (more usually) after running [`ths_ds_defrag`](../cli/ths_ds_defrag.md).

## Reshaping disagg_values

`disagg_values` is stored as a flat list. Use `to_ndarray()` to reshape it into an N-D array with axes ordered by `disagg_bins`:

```python
from toshi_hazard_store import query
from toshi_hazard_store.model.constraints import ProbabilityEnum

bins = {
    "mag": ["5.5", "6.5", "7.5"],
    "dist": ["10.0", "50.0", "100.0", "200.0"],
    "eps": ["-1.0", "0.0", "1.0"],
}

for disagg in query.get_disagg_aggregates(
    location_codes=["-41.300~174.800"],
    vs30s=[400],
    hazard_model="NSHM_v1.0.4",
    imts=["PGA"],
    aggs=["mean"],
    target_aggrs=["mean"],
    probabilities=[ProbabilityEnum._10_PCT_IN_50YRS],
    disagg_bins=bins,
    strategy="d2",
):
    arr = disagg.to_ndarray()   # shape: (3, 4, 3) for mag × dist × eps
    print(arr.shape)
```

The flat storage form is preserved as the canonical representation; reshaping is opt-in and allocates a numpy array on demand.

## Constraint Enums

### Probability Enum

::: toshi_hazard_store.model.constraints.ProbabilityEnum
