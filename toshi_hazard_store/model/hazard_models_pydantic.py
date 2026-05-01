"""The hazard metatdata models for (de)serialisation as json."""

from datetime import datetime, timezone
from math import prod
from typing import List

import pyarrow as pa
from lancedb.pydantic import pydantic_to_schema
from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.oq_import.aws_ecr_docker_image import AwsEcrImage

USE_64BIT_VALUES = False


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
    """Records characteristics of Hazard Curve producers/engines for compatibility and reproducibility.

    For hazard curve compatibility, we use both:
        - compatible_calc_fk: curves sharing this fk are `compatible` because the software/science is compatible.
        - config_digest: the config digest tells us the PSHA software configuration is compatible
          (see nzshm-model for details).

    For hazard curve reproducibility, use both:
        - ecr_image_digest: a hexdigest from the ecr_image (this is stored in the dataset).
        - ecr_image: we can run the same inputs against this Docker image to reproduce the outputs.

    Attributes:
        compatible_calc_fk: Foreign key to a CompatibleHazardCalculation (must map to a valid unique_id).
        ecr_image_digest: Docker image digest (sha256:...).
        config_digest: Configuration digest.
        created_at: The date and time this record was created. Defaults to utcnow.
        updated_at: The date and time this record was last updated. Defaults to utcnow.
        ecr_image: Optional AwsEcrImage for reproducibility.
        notes: Optional additional information.

    POSSIBLE in future:
        - if necessary we can extend this with a GithubRef / DockerImage alternative to AwsEcrImage.
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

    @field_validator("values", mode="before")
    @classmethod
    def validate_len_values(cls, value: List) -> List:
        if not len(value) == 44:
            raise ValueError(f"expected 44 values but there are {len(value)}")
        return value

    @staticmethod
    def pyarrow_schema() -> pa.schema:
        """A pyarrow schema for aggregate hazard curve datasets.

        built dynamically from the pydantic model, using lancedb helper method.
        """

        # Convert the Pydantic model to a PyArrow schema
        arrow_schema = pydantic_to_schema(HazardAggregateCurve)
        if not USE_64BIT_VALUES:
            arrow_schema = arrow_schema.set(
                arrow_schema.get_field_index("vs30"),
                pa.lib.field("vs30", pa.int32(), nullable=False),
            )
            arrow_schema = arrow_schema.set(
                arrow_schema.get_field_index("values"),
                pa.lib.field("values", pa.list_(pa.float32()), nullable=False),
            )

        return arrow_schema


class DisaggregationAggregate(BaseModel):
    """Aggregated disaggregation arrays across realisations.

    Attributes:
        compatible_calc_id: FK for hazard-calc equivalence.
        hazard_model_id: NSHM hazard model identifier e.g. "NSHM_v1.0.4" (caller-supplied).
        bins_digest: sha256[:16] over sorted axes + sorted bin centres (compatibility key).
        nloc_001: location string at 0.001° resolution e.g. "-38.330~175.550".
        nloc_0: location string at 1.0° resolution (used for partitioning).
        vs30: VS30 value in m/s.
        imt: intensity measure type label e.g. "PGA", "SA(1.0)".
        target_aggr: hazard-curve aggregation the disagg was conditioned on e.g. "mean", "0.5".
        probability: ProbabilityEnum name supplied by caller e.g. "_10_PCT_IN_50YRS".
        imtl: IML at which the disagg was computed.
        aggr: aggregation type applied across realisations e.g. "mean", "0.1".
        disagg_bins: ordered map ``{axis_name: [bin_centre_str, ...]}`` — key order
            defines the axis order of ``disagg_values``; values are stringified bin centres.
        disagg_values: flattened disaggregation array over ``disagg_bins`` axes, C-order.
    """

    compatible_calc_id: str
    hazard_model_id: str
    bins_digest: str
    nloc_001: str
    nloc_0: str
    vs30: int
    imt: str
    target_aggr: str
    probability: ProbabilityEnum
    imtl: float
    aggr: str
    disagg_bins: dict[str, list[str]]
    disagg_values: List[float]

    @field_serializer("probability")
    def serialize_probability(self, value: ProbabilityEnum) -> str:
        return value.name

    @field_validator("disagg_bins")
    @classmethod
    def validate_bins_nonempty(cls, value: dict) -> dict:
        if not value:
            raise ValueError("disagg_bins must not be empty")
        return value

    @model_validator(mode="after")
    def validate_values_shape(self) -> "DisaggregationAggregate":
        expected = prod(len(v) for v in self.disagg_bins.values())
        if len(self.disagg_values) != expected:
            raise ValueError(
                f"disagg_values length {len(self.disagg_values)} does not match product of bin sizes {expected}"
            )
        return self

    @staticmethod
    def pyarrow_schema() -> pa.schema:
        """A pyarrow schema for aggregate disaggregation datasets."""
        from toshi_hazard_store.model.pyarrow.dataset_schema import get_disagg_aggregate_schema

        return get_disagg_aggregate_schema()
