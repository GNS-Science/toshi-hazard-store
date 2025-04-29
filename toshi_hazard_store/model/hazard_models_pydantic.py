"""the hazard metatdata models for (de)serialisation as json."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


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
