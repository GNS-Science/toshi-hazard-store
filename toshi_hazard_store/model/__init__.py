import logging
from typing import Type

from . import location_indexed_model, revision_4
from .attributes import IMTValuesAttribute, LevelValuePairAttribute
from .constraints import AggregationEnum, IntensityMeasureTypeEnum, ProbabilityEnum, VS30Enum
from .disagg_models import DisaggAggregationExceedance, DisaggAggregationOccurence
from .disagg_models import drop_tables as drop_disagg
from .disagg_models import migrate as migrate_disagg
from .gridded_hazard import GriddedHazard
from .gridded_hazard import drop_tables as drop_gridded
from .gridded_hazard import migrate as migrate_gridded

log = logging.getLogger(__name__)


def migrate():
    """Create the tables, unless they exist already."""
    migrate_gridded()
    migrate_disagg()


def drop_tables():
    """Drop em"""
    drop_gridded()
    drop_disagg()
