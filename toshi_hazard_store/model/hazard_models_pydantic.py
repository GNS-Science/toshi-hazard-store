"""the hazard metatdata models are pydantic for (de)serialisaiton as json."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class CompatibleHazardCalculation(BaseModel):
    """Provides a unique identifier for compatible Hazard Calculations"""

    model_config = dict(populate_by_name=True)

    unique_id: str = Field(..., alias="unique_id")
    notes: str | None = Field(None, alias="notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HazardCurveProducerConfig(BaseModel):
    """Records characteristics of Hazard Curve producers/engines for compatibility tracking"""

    model_config = dict(populate_by_name=True)

    unique_id: str = Field(..., alias="unique_id")
    compatible_calc_fk: str = Field(
        ..., alias="compatible_calc_fk"
    )  # must map to a valid CompatibleHazardCalculation.unique_id

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    effective_from: datetime | None = Field(None, alias="effective_from")
    last_used: datetime | None = Field(None, alias="last_used")

    tags: list[str] | None = Field(None, alias="tags")

    producer_software: str = Field(..., alias="producer_software")
    producer_version_id: str = Field(..., alias="producer_version_id")
    configuration_hash: str = Field(alias="configuration_hash")
    configuration_data: str | None = Field(None, alias="configuration_data")

    imts: list[str] | None = Field(None, alias="imts")  # EnumConstrainedUnicodeAttribute(IntensityMeasureTypeEnum))
    imt_levels: list[float] | None = Field(None, alias="imt_levels")
    notes: str | None = Field(None, alias="notes")
