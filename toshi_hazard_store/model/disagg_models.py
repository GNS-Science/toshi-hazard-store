"""This module defines the pynamodb tables used to store openquake data. Third iteration"""

import logging
from datetime import datetime, timezone
from enum import Enum

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
    """Defines the values available for Aggregations."""

    MEAN = 'mean'
    COV = 'cov'
    _10 = '0.1'
    _20 = '0.2'
    _50 = '0.5'
    _80 = '0.8'
    _90 = '0.9'


class ProbabilityEnum(Enum):
    """
    Defines the values available for probabilities.

    store values as float representing probability in 1 year
    """

    TEN_PCT_IN_50YRS = 0.00456
    TWO_PCT_IN_50YRS = 0.00056


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
        self.sort_key = f'{self.nloc_001}:{vs30s}:{self.imt}:{self.hazard_agg}:{self.disagg_agg}:{self.hazard_model_id}'
        return self


class DisaggAggregationExceedance(DisaggAggregationBase):
    class Meta:
        billing_mode = 'PAY_PER_REQUEST'
        table_name = f"THS_DisaggAggregationExceedance-{DEPLOYMENT_STAGE}"
        region = REGION
        if IS_OFFLINE:
            host = "http://localhost:8000"  # pragma: no cover


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
