# Query API

The `toshi_hazard_store.query` module provides the main public interface for querying hazard data from parquet datasets.

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

## Main Query Functions

### ::: toshi_hazard_store.query.get_hazard_curves

Retrieves aggregated hazard curves from the dataset with multiple query strategies.

### ::: toshi_hazard_store.query.get_gridded_hazard

Retrieves gridded hazard data from parquet datasets.

## Data Models

These models represent the data returned by query functions:

### ::: toshi_hazard_store.query.AggregatedHazard

Represents an aggregated hazard curve with IMT values.

### ::: toshi_hazard_store.query.IMTValue

Represents a single intensity measure type value.

## Location Utilities

Helper functions for working with location codes:

### ::: toshi_hazard_store.query.downsample_code

Converts a location code to a lower resolution.

### ::: toshi_hazard_store.query.get_hashes

Computes location hashes at a specified resolution.

## Advanced: Dataset Access

For advanced use cases, you can access datasets directly:

### ::: toshi_hazard_store.query.get_dataset

Access the aggregated hazard dataset.

### ::: toshi_hazard_store.query.get_gridded_dataset

Access the gridded hazard dataset.

### ::: toshi_hazard_store.query.get_dataset_vs30

Access dataset for a specific VS30 value.

### ::: toshi_hazard_store.query.get_dataset_vs30_nloc0

Access dataset for specific VS30 and nloc0 partitioning.

## Query Strategies (Internal)

The query module supports multiple strategies for accessing data:

- **naive**: Let PyArrow handle partitioning automatically (default)
- **d1**: Use VS30 partitioning for better performance with large datasets
- **d2**: Use VS30 + nloc0 partitioning for optimal performance in constrained environments

These strategies are selected via the `strategy` parameter on `get_hazard_curves()`.
