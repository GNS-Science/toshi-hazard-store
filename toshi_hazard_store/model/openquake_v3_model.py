"""This module defines the pynamodb tables used to store openquake data. Third iteration"""

import logging
import uuid
from datetime import datetime, timezone

from nzshm_common.location.code_location import CodedLocation
from pynamodb.attributes import (
    JSONAttribute,
    ListAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UnicodeSetAttribute,
    VersionAttribute,
)
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from pynamodb.models import Model
from pynamodb_attributes import FloatAttribute, IntegerAttribute, TimestampAttribute

from toshi_hazard_store.config import DEPLOYMENT_STAGE, IS_OFFLINE, REGION
from toshi_hazard_store.model.openquake_v2_model import IMTValuesAttribute


def datetime_now():
    return datetime.now(tz=timezone.utc)


log = logging.getLogger(__name__)


class ToshiOpenquakeMeta(Model):
    """Stores metadata from the job configuration and the oq HDF5."""

    class Meta:
        """DynamoDB Metadata."""

        billing_mode = 'PAY_PER_REQUEST'
        table_name = f"THS_WIP_OpenquakeMeta-{DEPLOYMENT_STAGE}"
        region = REGION
        if IS_OFFLINE:
            host = "http://localhost:8000"  # pragma: no cover

    partition_key = UnicodeAttribute(hash_key=True)  # a static value as we actually don't want to partition our data
    hazsol_vs30_rk = UnicodeAttribute(range_key=True)

    version = VersionAttribute()
    created = TimestampAttribute(default=datetime_now)

    hazard_solution_id = UnicodeAttribute()
    general_task_id = UnicodeAttribute()
    vs30 = NumberAttribute()  # vs30 value

    imts = UnicodeSetAttribute()  # list of IMTs
    locations_id = UnicodeAttribute()  # Location codes identifier (ENUM?)
    source_ids = UnicodeSetAttribute()
    source_tags = UnicodeSetAttribute()
    inv_time = NumberAttribute()  # Invesigation time in years

    # extracted from the OQ HDF5
    src_lt = JSONAttribute()  # sources meta as DataFrame JSON
    gsim_lt = JSONAttribute()  # gmpe meta as DataFrame JSON
    rlz_lt = JSONAttribute()  # realization meta as DataFrame JSON

    # def hazard_solution_index(self):
    #     _class, _id = from_global_id(self.hazard_solution_id)
    #     return _id

    # def general_task_index(self):
    #     _class, _id = from_global_id(self.general_task_id)
    #     return _id


class vs30_nloc1_gt_rlz_index(LocalSecondaryIndex):
    """
    Local secondary index with vs#) + 0.1 Degree search resolution
    """

    class Meta:
        # All attributes are projected
        projection = AllProjection()

    partition_key = UnicodeAttribute(hash_key=True)  # Same as the base table
    index1_rk = UnicodeAttribute(range_key=True)


class vs30_nloc001_gt_rlz_index(LocalSecondaryIndex):
    """
    Local secondary index with vs30:nloc_001:gtid:rlz6) 0.001 Degree search resolution
    """

    class Meta:
        # All attributes are projected
        projection = AllProjection()

    partition_key = UnicodeAttribute(hash_key=True)  # Same as the base table
    index2_rk = UnicodeAttribute(range_key=True)


class HazardAggregation(Model):
    """Stores the individual hazard realisation curves."""

    class Meta:
        """DynamoDB Metadata."""

        billing_mode = 'PAY_PER_REQUEST'
        table_name = f"THS_WIP_OpenquakeRealization-{DEPLOYMENT_STAGE}"
        region = REGION
        if IS_OFFLINE:
            host = "http://localhost:8000"  # pragma: no cover

    partition_key = UnicodeAttribute(hash_key=True)  # For this we will use a downsampled location to 1.0 degree
    sort_key = UnicodeAttribute(range_key=True)
    aggregation_id = UnicodeAttribute()

    version = VersionAttribute()
    uniq_id = UnicodeAttribute()

    nloc_001 = UnicodeAttribute()  # 0.001
    nloc_01 = UnicodeAttribute()  # 0.01
    nloc_1 = UnicodeAttribute()  # 0.1
    nloc_0 = UnicodeAttribute()  # 1.0
    vs30 = IntegerAttribute()  # vs30 in m/s

    lat = FloatAttribute()  # latitude decimal degrees
    lon = FloatAttribute()  # longitude decimal degrees

    # aggregation_info = # details about the aggregation
    # count of aggregated items
    # aggregation configuration: filtering, grouping
    # subject: rlzs or aggregations
    # requested
    # time_seconds:
    # started:

    values = ListAttribute(of=IMTValuesAttribute)
    created = TimestampAttribute(default=datetime_now)


class OpenquakeRealization(Model):
    """Stores the individual hazard realisation curves."""

    class Meta:
        """DynamoDB Metadata."""

        billing_mode = 'PAY_PER_REQUEST'
        table_name = f"THS_WIP_OpenquakeRealization-{DEPLOYMENT_STAGE}"
        region = REGION
        if IS_OFFLINE:
            host = "http://localhost:8000"  # pragma: no cover

    partition_key = UnicodeAttribute(hash_key=True)  # For this we will use a downsampled location to 1.0 degree
    sort_key = UnicodeAttribute(range_key=True)  # TODO: check we can actually use this in queries!
    version = VersionAttribute()
    uniq_id = UnicodeAttribute()
    hazard_solution_id = UnicodeAttribute()

    nloc_001 = UnicodeAttribute()  # 0.001
    nloc_01 = UnicodeAttribute()  # 0.01
    nloc_1 = UnicodeAttribute()  # 0.1
    nloc_0 = UnicodeAttribute()  # 1.0
    # nloc_10 = UnicodeAttribute()  # 10.0

    rlz = IntegerAttribute()  # index to the openquake realization
    vs30 = IntegerAttribute()  # vs30 in m/s

    lat = FloatAttribute()  # latitude decimal degrees
    lon = FloatAttribute()  # longitude decimal degrees

    source_tags = UnicodeSetAttribute()
    source_ids = UnicodeSetAttribute()

    values = ListAttribute(of=IMTValuesAttribute)
    created = TimestampAttribute(default=datetime_now)

    # Secondary Index attributes
    index1 = vs30_nloc1_gt_rlz_index()
    index1_rk = UnicodeAttribute()

    def set_location(self, location: CodedLocation):
        """Set internal fields, indices etc from the location."""

        self.nloc_001 = location.downsample(0.001).code
        self.nloc_01 = location.downsample(0.01).code
        self.nloc_1 = location.downsample(0.1).code
        self.nloc_0 = location.downsample(1.0).code
        # self.nloc_10 = location.downsample(10.0).code

        self.partition_key = self.nloc_1

        self.lat = location.lat
        self.lon = location.lon

        rlzs = str(self.rlz).zfill(6)
        vs30s = str(self.vs30).zfill(3)

        self.sort_key = f'{self.nloc_001}:{vs30s}:{rlzs}:{self.hazard_solution_id}'
        self.index1_rk = f'{self.nloc_1}:{vs30s}:{rlzs}:{self.hazard_solution_id}'
        self.uniq_id = str(uuid.uuid4())


tables = [OpenquakeRealization, ToshiOpenquakeMeta]


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
