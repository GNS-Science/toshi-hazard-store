# Query API

The `toshi_hazard_store.query` package provides the main public interface for querying hazard data from parquet datasets.

## Quick Start

```python
from toshi_hazard_store import query

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