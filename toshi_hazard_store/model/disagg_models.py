"""This module defines the pynamodb tables used to store openquake data. Third iteration"""

import logging
from datetime import datetime, timezone
from enum import Enum

import numpy as np
from nzshm_common.location.code_location import CodedLocation
from pynamodb.attributes import UnicodeAttribute
from pynamodb_attributes import FloatAttribute

from toshi_hazard_store.config import DEPLOYMENT_STAGE, IS_OFFLINE, REGION

from .attributes import CompressedPickleAttribute, EnumAttribute, PickleAttribute, UnicodeEnumConstrainedAttribute
from .location_indexed_model import VS30_KEYLEN, LocationIndexedModel


def datetime_now():
    return datetime.now(tz=timezone.utc)


log = logging.getLogger(__name__)


class AggregationEnum(Enum):
    """Defines the values available for aggregations."""

    MEAN = 'mean'
    COV = 'cov'
    STD = 'std'
    _005 = '0.005'
    _01 = '0.01'
    _025 = '0.025'
    _05 = '0.05'
    _10 = '0.1'
    _20 = '0.2'
    _30 = '0.3'
    _40 = '0.4'
    _50 = '0.5'
    _60 = '0.6'
    _70 = '0.7'
    _80 = '0.8'
    _90 = '0.9'
    _95 = '0.95'
    _975 = '0.975'
    _99 = '0.99'
    _995 = '0.995'


class ProbabilityEnum(Enum):
    """
    Defines the values available for probabilities.

    store values as float representing probability in 1 year
    """

    _86_PCT_IN_50YRS = 3.8559e-02
    _63_PCT_IN_50YRS = 1.9689e-02
    _39_PCT_IN_50YRS = 9.8372e-03
    _18_PCT_IN_50YRS = 3.9612e-03
    _10_PCT_IN_50YRS = 2.1050e-03
    _5_PCT_IN_50YRS = 1.0253e-03
    _2_PCT_IN_50YRS = 4.0397e-04
    _1_PCT_IN_50YRS = 2.0099e-04


class DisaggAggregationBase(LocationIndexedModel):
    """Store aggregated disaggregations."""

    hazard_model_id = UnicodeAttribute()
    imt = UnicodeAttribute()

    hazard_agg = UnicodeEnumConstrainedAttribute(AggregationEnum)  # eg MEAN
    disagg_agg = UnicodeEnumConstrainedAttribute(AggregationEnum)

    disaggs = CompressedPickleAttribute()  # a very compressible numpy array,
    bins = PickleAttribute()  # a much smaller numpy array

    shaking_level = FloatAttribute()

    probability = EnumAttribute(ProbabilityEnum)  # eg TEN_PCT_IN_50YRS

    def set_location(self, location: CodedLocation):
        """Set internal fields, indices etc from the location."""
        super().set_location(location)

        # update the indices
        vs30s = str(self.vs30).zfill(VS30_KEYLEN)
        self.partition_key = self.nloc_1
        self.sort_key = (
            f'{self.hazard_model_id}:{self.hazard_agg}:{self.disagg_agg}:'
            f'{self.nloc_001}:{vs30s}:{self.imt}:{self.probability.name}'
        )
        return self


class DisaggAggregationExceedance(DisaggAggregationBase):
    class Meta:
        billing_mode = 'PAY_PER_REQUEST'
        table_name = f"THS_DisaggAggregationExceedance-{DEPLOYMENT_STAGE}"
        region = REGION
        if IS_OFFLINE:
            host = "http://localhost:8000"  # pragma: no cover

    @staticmethod
    def new_model(
        hazard_model_id: str,
        location: CodedLocation,
        vs30: str,
        imt: str,
        hazard_agg: AggregationEnum,
        disagg_agg: AggregationEnum,
        probability: ProbabilityEnum,
        shaking_level: float,
        disaggs: np.ndarray,
        bins: np.ndarray,
    ) -> 'DisaggAggregationExceedance':
        obj = DisaggAggregationExceedance(
            hazard_model_id=hazard_model_id,
            vs30=vs30,
            imt=imt,
            hazard_agg=hazard_agg,
            disagg_agg=disagg_agg,
            probability=probability,
            shaking_level=shaking_level,
            disaggs=disaggs,
            bins=bins,
        )
        obj.set_location(location)
        return obj


class DisaggAggregationOccurence(DisaggAggregationBase):
    class Meta:
        billing_mode = 'PAY_PER_REQUEST'
        table_name = f"THS_DisaggAggregationOccurence-{DEPLOYMENT_STAGE}"
        region = REGION

        if IS_OFFLINE:
            host = "http://localhost:8000"  # pragma: no cover


tables = [
    DisaggAggregationExceedance,
    DisaggAggregationOccurence,
]


def migrate():
    """Create the tables, unless they exist already."""
    for table in tables:
        if not table.exists():  # pragma: no cover
            table.create_table(wait=True)
            print(f"Migrate created table: {table}")
            log.info(f"Migrate created table: {table}")


def drop_tables():
    """Drop the tables, if they exist."""
    for table in tables:
        if table.exists():  # pragma: no cover
            table.delete_table()
            log.info(f'deleted table: {table}')
