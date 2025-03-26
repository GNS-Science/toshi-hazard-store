"""the hazard metatdata models are pydantic for (de)serialisation as json."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class CompatibleHazardCalculation(BaseModel):
    """Provides a unique identifier for compatible Hazard Calculations"""

    unique_id: str  # NB Field(...) means that this field is required, no default value.
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HazardCurveProducerConfig(BaseModel):
    """Records characteristics of Hazard Curve producers/engines for compatibility tracking"""

    unique_id: str
    compatible_calc_fk: str  # must map to a valid CompatibleHazardCalculation.unique_id

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    effective_from: datetime | None = None
    last_used: datetime | None = None

    tags: list[str] | None = None

    producer_software: str
    producer_version_id: str
    configuration_hash: str | None
    configuration_data: str | None = None

    imts: list[str] | None = None  # EnumConstrainedUnicodeAttribute(IntensityMeasureTypeEnum))
    imt_levels: list[float] | None = None
    notes: str | None = Field(None)
