# Hazard Curves

These models represent aggregated hazard curves derived from OpenQuake PSHA engine outputs.

## Hazard Aggregate Curve

The core model for aggregated hazard curve data, stored as PyArrow parquet datasets.

::: toshi_hazard_store.model.hazard_models_pydantic.HazardAggregateCurve
    options:
      show_source: true
      members: false
      attributes: true

## PyArrow Schema

The `HazardAggregateCurve` model can be converted to a PyArrow schema for dataset I/O:

```python
from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve
schema = HazardAggregateCurve.pyarrow_schema()
```

The schema includes:

- `compatible_calc_id` (string) - Compatible calculation identifier
- `hazard_model_id` (string) - Model identifier (e.g., "NSHM_v1.0.4")
- `nloc_001` (string) - Location to 3 decimal places (e.g., "-38.330~17.550")
- `nloc_0` (string) - Location to 0 decimal places (e.g., "-38.0~17.0") for partitioning
- `imt` (string) - Intensity measure type (e.g., "PGA", "SA(5.0)")
- `vs30` (int32) - VS30 value
- `aggr` (string) - Aggregation type (e.g., "mean", "0.9", "std")
- `values` (list of float32) - 44 IMT level values

## Constraint Enums

These enumerations define valid values for model fields:

### Aggregation Enum

::: toshi_hazard_store.model.constraints.AggregationEnum

### Intensity Measure Type Enum

::: toshi_hazard_store.model.constraints.IntensityMeasureTypeEnum

### VS30 Enum

::: toshi_hazard_store.model.constraints.VS30Enum

### Probability Enum

::: toshi_hazard_store.model.constraints.ProbabilityEnum
