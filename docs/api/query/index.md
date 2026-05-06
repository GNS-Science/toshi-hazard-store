# Query API

The `toshi_hazard_store.query` package provides the main public interface for querying hazard data from parquet datasets.

## Quick Start

```python
from toshi_hazard_store import query
from toshi_hazard_store.model.constraints import ProbabilityEnum

# Query hazard curves
curves = query.get_hazard_curves(
    location_codes=["-41.300~174.800"],
    vs30s=[400],
    hazard_model="NSHM_v1.0.4",
    imts=["PGA"],
    aggs=["mean"],
    strategy="d1"  # or "d2", "naive"
)

for curve in curves:
    print(f"{curve.imt} at {curve.nloc_001}: {curve.values}")

# Query disaggregation aggregates
disaggs = query.get_disagg_aggregates(
    location_codes=["-41.300~174.800"],
    vs30s=[400],
    hazard_model="NSHM_v1.0.4",
    imts=["PGA"],
    aggs=["mean"],
    target_aggrs=["mean"],
    probabilities=[ProbabilityEnum._10_PCT_IN_50YRS],
    disagg_bins={
        "mag": ["5.5", "6.5", "7.5"],
        "dist": ["10.0", "50.0", "100.0", "200.0"],
        "eps": ["-1.0", "0.0", "1.0"],
    },
    strategy="d2"  # or "d1", "naive"
)

for disagg in disaggs:
    print(f"{disagg.imt} at {disagg.nloc_001}, prob={disagg.probability.name}")
    arr = disagg.to_ndarray()  # reshape to N-D array over disagg_bins axes
    print(f"  shape: {arr.shape}")

# Query gridded hazard
gridded = query.get_gridded_hazard(
    location_grid_id="NZ_0_1_NB_1_1",
    hazard_model_ids=["NSHM_v1.0.4"],
    vs30s=[400.0],
    imts=["PGA"],
    aggs=["mean"],
    poes=[0.02, 0.1]
)

for grid in gridded:
    print(f"Grid {grid.location_grid_id} at POE {grid.poe}: {len(grid.accel_levels)} locations")
```

## toshi_hazard_store.query package
::: toshi_hazard_store.query