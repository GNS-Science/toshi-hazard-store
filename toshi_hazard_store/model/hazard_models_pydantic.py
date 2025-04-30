"""The hazard metatdata models for (de)serialisation as json."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from toshi_hazard_store.oq_import.aws_ecr_docker_image import AwsEcrImage


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


# class ElasticContainerRegistryImage(BaseModel):
#     """A docker image stored to AWS ECR used to produce hazard curves.

#     NSHM docker images contain application build, sometimes with extra code
#     and maybe the hazard convertor.
#     """

#     image_uri: str
#     image_digest: str
#     tags: list[str] | None = None
#     pushed_at: datetime
#     last_pulled_at: datetime | None = None


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
     - if necessary we can extend this with a GithubRef / DockerImage alternative to ElasticContainerRegistryImage
    """

    unique_id: str
    compatible_calc_fk: str  # must map to a valid CompatibleHazardCalculation.unique_id
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    ecr_image: AwsEcrImage | None = None
    ecr_image_digest: str
    config_digest: str
    notes: str | None = None
