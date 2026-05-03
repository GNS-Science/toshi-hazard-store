# Usage

To use toshi-hazard-store in a project you must first:

- [Install the library](./installation.md), and
- [Configure it](./configuration.md) for your requirements (e.g., cloud use or local offline use)

## Import Realizations

Hazard curve realizations (curves for individual branches of the logic tree) can be imported from OpenQuake hdf5 and stored as parquet datasets with the [`ths_rlz_import`](cli/ths_rlz_import.md) script.
```console
ths_rlz_import store-hazard [OPTIONS] HDF5_PATH CONFIG_PATH COMPATIBLE_CALC_ID HAZARD_CALC_ID ECR_DIGEST OUTPUT
```
Realizations will be partitioned by unique ID (`HAZARD_CALC_ID`). To compact the dataset and re-partition for easy filtering use the [`ths_ds_defrag`](cli/ths_ds_defrag.md). The default partitioning works for hazard curve realizations.

Disaggregation realizations can be imported from OpenQuake hdf5 using ['ths_disagg_import'](cli/ths_disagg_import.md).
```console
ths_disagg_import store-disagg [OPTIONS] HDF5_PATH CONFIG_PATH COMPATIBLE_CALC_ID HAZARD_CALC_ID ECR_DIGEST OUTPUT \
  -P _2_PCT_IN_50YRS -M NSHM_v1.0.4 -A mean
```
When defragging a disaggregation dataset, the suggested partitioning is `bins_digest,vs30,nloc_0`, not the default `vs30,nloc_0`; this makes filtering for specific disaggregation types (e.g. magnitude and distance disaggregation vs TRT disaggregation) easier.
```console
ths_ds_defrag -v -p "bins_digest,vs30,nloc_0" /tmp/disagg-debug-out/ /tmp/disagg-defragg-rlz/
```

## Query the Hazard Store

The library provides two main query functions for retrieving hazard data from PyArrow parquet datasets.

### Get Hazard Curves

```python
from toshi_hazard_store import query

# Query aggregated hazard curves
curves = query.get_hazard_curves(
    location_codes=["-41.300~174.800", "-43.532~172.636"],  # Location codes (lat~lon)
    vs30s=[250, 400],                                        # VS30 values
    hazard_model="NSHM_v1.0.4",                              # Hazard model ID
    imts=["PGA", "SA(0.5)", "SA(1.0)"],                     # Intensity measure types
    aggs=["mean", "0.5", "std"],                            # Aggregation types
    strategy="d2"                                            # Query strategy (naive, d1, d2)
)

for curve in curves:
    print(f"Location: {curve.nloc_001}")
    print(f"  IMT: {curve.imt}, VS30: {curve.vs30}, Agg: {curve.agg}")
    print(f"  Values: {curve.values[:5]}...")  # First 5 of 44 values
```

### Query Strategies

The `strategy` parameter controls how the query accesses the dataset:

| Strategy | Description |
|----------|-------------|
| `naive` | Default. Lets PyArrow handle partitioning automatically. Good for small/medium datasets. |
| `d1` | Assumes dataset is partitioned on `vs30`. Generates multiple PyArrow queries. Better for large datasets. |
| `d2` | Assumes dataset is partitioned on `vs30, nloc_0`. Optimal for full NSHM with constrained resources (e.g., AWS Lambda). |

### Get Gridded Hazard

```python
from toshi_hazard_store import query

# Query gridded hazard data (interpolated acceleration levels at grid locations)
gridded = query.get_gridded_hazard(
    location_grid_id="NZ_0_1_NB_1_1",      # NSHM grid identifier
    hazard_model_ids=["NSHM_v1.0.4"],       # Hazard model IDs
    vs30s=[250.0, 400.0],                   # VS30 values
    imts=["PGA", "SA(1.0)"],                # Intensity measure types
    aggs=["mean"],                          # Aggregation types
    poes=[0.02, 0.1, 0.5]                   # Probabilities of exceedance
)

for grid in gridded:
    print(f"Grid: {grid.location_grid_id}")
    print(f"  IMT: {grid.imt}, VS30: {grid.vs30}, POE: {grid.poe}")
    print(f"  Acceleration levels: {len(grid.accel_levels)} locations")
```

### Data Models

The query functions return pydantic model instances:

- **`AggregatedHazard`**: Contains aggregated hazard curve data with 44 IMT level values
- **`GriddedHazardPoeLevels`**: Contains acceleration levels at grid locations for given POE values

### Location Utilities

Helper functions for working with location codes:

```python
from toshi_hazard_store.query import downsample_code, get_hashes

# Downsample a location code to different resolutions
loc = "-41.300~174.800"
print(downsample_code(loc, 0.1))   # "-41.3~174.8"
print(downsample_code(loc, 1.0))   # "-41.0~175.0"

# Generate location hashes at a specific resolution
locs = ["-41.300~174.800", "-43.532~172.636"]
hashes = list(get_hashes(locs, resolution=0.1))
```

## Configuration

Make sure to set the appropriate environment variables for your dataset location. See the [Configuration](./configuration.md) page for details.