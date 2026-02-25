# Hazard Metadata Models

These models manage metadata about hazard calculations and producers, stored as JSON files.

## Compatible Hazard Calculation

Provides a unique identifier for compatible hazard calculations (calculations that produce comparable results).

::: toshi_hazard_store.model.hazard_models_pydantic.CompatibleHazardCalculation
    options:
      show_source: true
      members: false
      attributes: true

## Hazard Curve Producer Config

Records characteristics of hazard curve producers/engines for compatibility and reproducibility.

::: toshi_hazard_store.model.hazard_models_pydantic.HazardCurveProducerConfig
    options:
      show_source: true
      members: false
      attributes: true

## Usage

These metadata models are used together to identify compatible hazard curves:

1. **CompatibleHazardCalculation** - Created when setting up a new hazard calculation
2. **HazardCurveProducerConfig** - Created when running a calculation, linked to a CompatibleHazardCalculation

Two hazard curves are considered "compatible" if they share the same `compatible_calc_id` and `config_digest`.

The managers handle CRUD operations via JSON files in the `resources/metadata/` directory.
