from .openquake_v1_model import (
    LevelValuePairAttribute,
    ToshiOpenquakeHazardCurveRlzs,
    ToshiOpenquakeHazardCurveStats,
    ToshiOpenquakeHazardMeta,
)
from .openquake_v1_model import drop_tables as drop_tables_v1
from .openquake_v1_model import migrate as migrate_v1
from .openquake_v1_model import tables as oqv1_tables
from .openquake_v2_model import IMTValuesAttribute, ToshiOpenquakeHazardCurveRlzsV2, ToshiOpenquakeHazardCurveStatsV2
from .openquake_v2_model import drop_tables as drop_tables_v2
from .openquake_v2_model import migrate as migrate_v2
from .openquake_v2_model import tables as oqv2_tables


def migrate():
    """Create the tables, unless they exist already."""
    migrate_v1()
    migrate_v2()


def drop_tables():
    """Drop em"""
    drop_tables_v1()
    drop_tables_v2()