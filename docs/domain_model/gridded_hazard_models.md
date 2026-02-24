# Gridded Hazard Models

These models represent hazard values interpolated at grid locations for given probabilities of exceedance.

## Gridded Hazard POE Levels

Hazard acceleration (shaking) levels at various grid locations for a given POE, investigation time, VS30, IMT, and aggregation.

::: toshi_hazard_store.model.gridded.gridded_hazard_pydantic.GriddedHazardPoeLevels
    options:
      show_source: true
      members: false
      attributes: true

## PyArrow Schema

The `GriddedHazardPoeLevels` model can be converted to a PyArrow schema for dataset I/O:

```python
from toshi_hazard_store.model.gridded.gridded_hazard_pydantic import GriddedHazardPoeLevels
schema = GriddedHazardPoeLevels.pyarrow_schema()
```

The schema includes:

- `compatible_calc_id` (string) - Compatible calculation identifier
- `hazard_model_id` (string) - Model identifier
- `location_grid_id` (string) - NSHM grid identifier (e.g., "NZ_0_1_NB_1_1")
- `imt` (string) - Intensity measure type (validated against `IntensityMeasureTypeEnum`)
- `vs30` (int32) - VS30 value (validated against `VS30Enum`)
- `aggr` (string) - Aggregation type (validated against `AggregationEnum`)
- `investigation_time` (int) - Must be 50 years
- `poe` (float) - Probability of exceedance (0 < poe < 1)
- `accel_levels` (list of float32) - Acceleration levels in G, aligned with grid locations
