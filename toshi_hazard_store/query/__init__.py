"""Query module for hazard data retrieval.

This module provides the main public interface for querying hazard data
from parquet datasets. It includes:

- Main query functions: get_hazard_curves, get_gridded_hazard
- Data models: AggregatedHazard, IMTValue
- Location utilities: downsample_code, get_hashes
- Advanced dataset access: get_dataset, get_gridded_dataset, etc.
"""

# Main query functions
from .datasets import get_gridded_hazard, get_hazard_curves

# Data models
from .models import AggregatedHazard, IMTValue

# Location utilities
from .hazard_query import downsample_code, get_hashes

# Dataset cache accessors (for advanced use)
from .dataset_cache import (
    get_dataset,
    get_dataset_vs30,
    get_dataset_vs30_nloc0,
    get_gridded_dataset,
)

# Configuration constants (for testing/mocking)
from toshi_hazard_store.config import DATASET_AGGR_URI, DATASET_GRIDDED_URI

__all__ = [
    # Main query functions
    "get_hazard_curves",
    "get_gridded_hazard",
    # Data models
    "AggregatedHazard",
    "IMTValue",
    # Location utilities
    "downsample_code",
    "get_hashes",
    # Dataset cache accessors
    "get_dataset",
    "get_dataset_vs30",
    "get_dataset_vs30_nloc0",
    "get_gridded_dataset",
    # Configuration constants
    "DATASET_AGGR_URI",
    "DATASET_GRIDDED_URI",
]
