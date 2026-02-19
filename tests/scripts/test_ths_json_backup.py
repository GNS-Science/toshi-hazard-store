"""Tests for ths_json_backup script functions."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from toshi_hazard_store.scripts import ths_json_backup
from toshi_hazard_store.query.models import AggregatedHazard, IMTValue


@pytest.fixture
def sample_aggregated_hazard():
    """Create a sample AggregatedHazard object for testing."""
    return AggregatedHazard(
        compatable_calc_id="test_calc_001",
        hazard_model_id="NSHM_v1.0.4",
        nloc_001="-41.300~174.800",
        nloc_0="-41.0~174.0",
        imt="PGA",
        vs30=400,
        agg="mean",
        values=[IMTValue(lvl=0.0001, val=0.0001) for _ in range(44)],
    )


def test_init_processed_marking():
    """Test the init_processed_marking function."""
    # This function initializes the processed files log
