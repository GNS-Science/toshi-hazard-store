import logging
from typing import Type

from .constraints import AggregationEnum, IntensityMeasureTypeEnum, ProbabilityEnum, VS30Enum
from .gridded_hazard import GriddedHazard
from .gridded_hazard import drop_tables as drop_gridded
from .gridded_hazard import migrate as migrate_gridded

log = logging.getLogger(__name__)


def migrate():
    """Create the tables, unless they exist already."""
    migrate_gridded()


def drop_tables():
    """Drop em"""
    drop_gridded()
