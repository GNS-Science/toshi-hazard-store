"""The gridded hazard models for (de)serialisation as json."""

from typing import Any, List

import numpy as np
import pyarrow as pa
from lancedb.pydantic import pydantic_to_schema
from nzshm_common import grids
from pydantic import BaseModel, field_validator, model_validator

from ..constraints import AggregationEnum, IntensityMeasureTypeEnum, VS30Enum

DISABLE_GRIDDED_MODEL_VALIDATOR = False
USE_64BIT_VALUES = False


class GriddedHazardPoeLevels(BaseModel):
    """A list of hazard acceleration (shaking) at various locations in a grid.

    Ground shaking levels for the given location_grid at the given poe, investigation time, vs30, imt and aggr.

    NB the validator methods on this model are 'rigorous and slow', for use when creating new model instances.
    If models that are being rehydrated from trusted source can use the pydantic use the `model_construct` method
    to avoid the validatoin overhead.

    Attributes:
        compatible_calc_id: for hazard-calc equivalence.
        hazard_model_id: the model that the values are derived from.
        location_grid_id: the NSHM grid identifier.
        imt: the imt label e.g. `PGA`, `SA(5.0)`.
        vs30: the VS30 value.
        aggr: the aggregation type. e.g `mean`, `0.9`, `0.95`.
        investigation_time: the time period (in years) for which the poe applies.
        poe: the Probability of Exceedance (poe) expressed as a normalized percentage (i.e 0 to 1.0).
        accel_levels: a list of floats representing the acceleration level in G at the given poe for each grid location.
           This list must align with the locations in the given `location_grid_id`.
    """

    compatible_calc_id: str
    hazard_model_id: str
    location_grid_id: str
    imt: str
    vs30: int
    aggr: str
    investigation_time: int
    poe: float
    accel_levels: List[float]

    @field_validator('vs30', mode='before')
    @classmethod
    def validate_vs30_value(cls, value: int) -> int:
        if value not in [x.value for x in VS30Enum]:
            raise ValueError(f'vs30 value {value} is not supported.')
        return value

    @field_validator('imt', mode='before')
    @classmethod
    def validate_imt_value(cls, value: str) -> str:
        if value not in [x.value for x in IntensityMeasureTypeEnum]:
            raise ValueError(f'imt value {value} is not supported.')
        return value

    @field_validator('aggr', mode='before')
    @classmethod
    def validate_aggr_value(cls, value: str) -> str:
        if value not in [x.value for x in AggregationEnum]:
            raise ValueError(f'aggr value {value} is not supported.')
        return value

    @field_validator('investigation_time', mode='before')
    @classmethod
    def validate_investigation_time_value(cls, value: int) -> int:
        if not value == 50:
            raise ValueError(f'investigation time must be 50 years. {value} is not supported')
        return value

    @field_validator('poe', mode='before')
    @classmethod
    def validate_poe_value(cls, value: float) -> float:
        if not (0 < value < 1):
            raise ValueError(f'poe value {value} is not supported.')
        return value

    @field_validator('accel_levels', mode='before')
    @classmethod
    def validate_accel_levels_value(cls, value: List[Any]) -> List[Any]:
        GriddedHazardPoeLevels.validate_grid_accel_levels(value)
        return value

    @model_validator(mode='before')
    def validate_len_accel_levels(cls, data) -> List:
        if DISABLE_GRIDDED_MODEL_VALIDATOR:
            return data
        else:
            grid = grids.get_location_grid(data['location_grid_id'])
            if not len(data['accel_levels']) == len(grid):
                raise ValueError(
                    f"expected accel_levels to have `{len(grid)}` values, but found: {len(data['accel_levels'])}"
                )
            return data  # pragma: no cover

    @staticmethod
    def pyarrow_schema() -> pa.schema:
        """A pyarrow schema for the pydantic model.

        built dynamically from the pydantic model, using lancedb helper method.
        """

        # Convert the Pydantic model to a PyArrow schema
        arrow_schema = pydantic_to_schema(GriddedHazardPoeLevels)
        if not USE_64BIT_VALUES:
            arrow_schema = arrow_schema.set(
                arrow_schema.get_field_index('accel_levels'),
                pa.lib.field('accel_levels', pa.list_(pa.float32()), nullable=False),
            )
        return arrow_schema

    @staticmethod
    def validate_grid_accel_levels(values_list):
        errs = []
        vals = []
        for idx, val in enumerate(values_list):
            if not isinstance(val, (np.float32, float)):
                errs.append(val)
            else:
                vals.append(val)
        if len(errs):
            raise ValueError(
                f"list members non-floats {len(errs)} ; floats {len(vals)}.]\n"
                f"First ten bad: {[x for x in errs[:10]]}.\n"
                f"First 10 OK: {[x for x in vals[:10]]}."
            )
