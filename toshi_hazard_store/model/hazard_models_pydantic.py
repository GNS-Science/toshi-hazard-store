"""The hazard metatdata models for (de)serialisation as json."""

from datetime import datetime, timezone
from typing import List

import pyarrow as pa
from lancedb.pydantic import pydantic_to_schema
from pydantic import BaseModel, Field, field_validator

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
