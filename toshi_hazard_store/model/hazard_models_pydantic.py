"""The hazard metatdata models for (de)serialisation as json."""

from datetime import datetime, timezone
from typing import List

from nzshm_common.grids import RegionGrid
from pydantic import BaseModel, Field, field_validator, model_validator

from toshi_hazard_store.oq_import.aws_ecr_docker_image import AwsEcrImage

# Float32 = Annotated[float, {"pyarrow_type": pyarrow.float32()}]
# Int32 = Annotated[int, {"pyarrow_type": pyarrow.int32()}]
from .constraints import AggregationEnum, IntensityMeasureTypeEnum, VS30Enum


class CompatibleHazardCalculation(BaseModel):
    """
    Provides a unique identifier for compatible Hazard Calculations.

    Attributes:
        unique_id: A unique identifier for the Hazard Calculation.
        notes (optional): Additional information about the Hazard Calculation.
        created_at: The date and time this record was created. Defaults to utcnow.
        updated_at: The date and time this record was last updated. Defaults to utcnow.
    """

    unique_id: str  # NB Field(...) means that this field is required, no default value.
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HazardCurveProducerConfig(BaseModel):
    """Records characteristics of Hazard Curve producers/engines for compatibility and reproducablity.

    for hazard curve compatability, we use both:
        - compatible_calc_fk: curves sharing this fk are `compatible` because the software/science is compatible.
        - configuration_hash: the config hash tells us the the PSHA software configuration is compatible.
          (see nzshm-model for details)

    for hazard curve reproducability, use both:
         - ecr_image_digest: a hexdigest from the ecr_image (this is stored in the dataset)
         - ecr_image: we can run the same inputs against this docker image to reproduce the outputs AND

    POSSIBLE in future:
     - if necessary we can extend this with a GithubRef / DockerImage alternative to AwsEcrImage
    """

    compatible_calc_fk: str  # must map to a valid CompatibleHazardCalculation.unique_id
    ecr_image_digest: str
    config_digest: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    ecr_image: AwsEcrImage | None = None
    notes: str | None = None

    @property
    def unique_id(self) -> str:
        """The unique ID should not include any non cross-platform characters (for filename compatablity)."""
        assert self.ecr_image_digest[:7] == "sha256:"
        return self.ecr_image_digest[7:]


class HazardAggregateCurve(BaseModel):
    """Generally these are aggregated realisation curves.

    Attributes:
        compatible_calc_id: for hazard-calc equivalence.
        model_id: the model that these curves represent.
        nloc_001:  the location string to three places e.g. "-38.330~17.550".
        nloc_0:  the location string to zero places e.g.  "-38.0~17.0" (used for partitioning).
        imt: the imt label e.g. 'PGA', 'SA(5.0)'
        vs30: the VS30 integer
        aggr: the aggregation type
        values: a list of the 44 IMTL values
    """

    compatible_calc_id: str
    hazard_model_id: str
    nloc_001: str
    nloc_0: str
    imt: str
    vs30: int
    aggr: str
    values: List[float]

    @field_validator('values', mode='before')
    @classmethod
    def validate_len_values(cls, value: List) -> List:
        if not len(value) == 44:
            raise ValueError(f'expected 44 values but there are {len(value)}')
        return value


class GriddedHazardPoeLevels(BaseModel):
    """A list of hazard acceleration (shaking) at various locations in a grid.

    Ground shaking levels for the given location_grid at the given poe, investigation time, vs30, imt and aggr.

    Attributes:
        compatible_calc_id: for hazard-calc equivalence.
        hazard_model_id: the model that the values are derived from.
        location_grid_id: the NSHM grid identifier.
        imt: the imt label e.g. `PGA`, `SA(5.0)`.
        vs30: the VS30 value.
        aggr: the aggregation type. e.g `mean`, `0.9`, `0.95`.
        investigation_time: the time period (in years) for which the poe applies.
        poe: the Probability of Exceedance (poe) expressed as a coeeffient/percentage/ratio (??).
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

    accel_levels: List[float]  # was grid_poes, but this was incrreect

    @field_validator('vs30', mode='before')
    # @classmethod
    def validate_vs30_value(cls, value: int) -> int:
        if value not in VS30Enum:
            raise ValueError(f'vs30 value {value} is not supported')
        return value

    @field_validator('imt', mode='before')
    # @classmethod
    def validate_imt_value(cls, value: str) -> str:
        if value not in IntensityMeasureTypeEnum:
            raise ValueError(f'imt value {value} is not supported')
        return value

    @field_validator('aggr', mode='before')
    # @classmethod
    def validate_aggr_value(cls, value: str) -> str:
        if value not in AggregationEnum:
            raise ValueError(f'aggr value {value} is not supported')
        return value

    @field_validator('investigation_time', mode='before')
    # @classmethod
    def validate_investigation_time_value(cls, value: int) -> int:
        if not value == 50:
            raise ValueError(f'investigation time must be 50 years. {value} is not supported')
        return value

    @model_validator(mode='before')
    def validate_len_accel_levels(cls, data) -> List:
        grid = RegionGrid[data.location_grid_id]
        if not len(data.accel_levels) == len(grid):
            raise ValueError(f'expected accel_levels to have `{len(grid)}` values but found: {len(data.accel_levels)}')
        return data
