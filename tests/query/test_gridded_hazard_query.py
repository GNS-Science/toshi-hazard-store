"""Tests for get_gridded_hazard query function."""

import os
from pathlib import Path

import pytest

from toshi_hazard_store.model.gridded import gridded_hazard_pydantic
from toshi_hazard_store.query import dataset_cache, datasets


@pytest.mark.parametrize("use64bit", [True, False])
def test_get_gridded_hazard_basic(get_one_degree_region_grid_fixture, monkeypatch, use64bit):
    """Test basic functionality of get_gridded_hazard function."""
    # Setup test fixtures
    dataset_folder = Path(Path(os.path.realpath(__file__)).parent.parent, "fixtures", "gridded_hazard", "DS")

    monkeypatch.setattr(dataset_cache, "DATASET_GRIDDED_URI", str(dataset_folder.absolute()))
    monkeypatch.setattr(gridded_hazard_pydantic, "DISABLE_GRIDDED_MODEL_VALIDATOR", True)
    monkeypatch.setattr(gridded_hazard_pydantic, "USE_64BIT_VALUES", use64bit)

    # Test parameters
    location_grid_id = "NZ_0_1_NB_1_1"
    hazard_model_ids = ["NSHM_v1.0.4"]
    vs30s = [400.0]  # Convert to float
    imts = ["PGA"]
    aggs = ["mean"]
    poes = [0.02]

    # Call the function under test
    gridded_hazards = list(
        datasets.get_gridded_hazard(
            location_grid_id=location_grid_id,
            hazard_model_ids=hazard_model_ids,
            vs30s=vs30s,
            imts=imts,
            aggs=aggs,
            poes=poes,
        )
    )

    # Basic assertions
    assert len(gridded_hazards) > 0, "Should return at least one gridded hazard record"

    for ghaz in gridded_hazards:
        # Check that all required fields are present
        assert hasattr(ghaz, "location_grid_id")
        assert hasattr(ghaz, "hazard_model_id")
        assert hasattr(ghaz, "vs30")
        assert hasattr(ghaz, "imt")
        assert hasattr(ghaz, "aggr")
        assert hasattr(ghaz, "poe")
        assert hasattr(ghaz, "accel_levels")

        # Check that values are reasonable
        assert ghaz.location_grid_id == location_grid_id
        assert ghaz.hazard_model_id in hazard_model_ids
        assert ghaz.vs30 in vs30s
        assert ghaz.imt in imts
        assert ghaz.aggr in aggs
        assert ghaz.poe in poes
        assert ghaz.accel_levels is not None


@pytest.mark.parametrize("use64bit", [True, False])
def test_get_gridded_hazard_multiple_parameters(get_one_degree_region_grid_fixture, monkeypatch, use64bit):
    """Test get_gridded_hazard with multiple parameter values."""
    # Setup test fixtures
    dataset_folder = Path(Path(os.path.realpath(__file__)).parent.parent, "fixtures", "gridded_hazard", "DS")

    monkeypatch.setattr(dataset_cache, "DATASET_GRIDDED_URI", str(dataset_folder.absolute()))
    monkeypatch.setattr(gridded_hazard_pydantic, "DISABLE_GRIDDED_MODEL_VALIDATOR", True)
    monkeypatch.setattr(gridded_hazard_pydantic, "USE_64BIT_VALUES", use64bit)

    # Test parameters with multiple values
    location_grid_id = "NZ_0_1_NB_1_1"
    hazard_model_ids = ["NSHM_v1.0.4"]
    vs30s = [400.0, 750.0]  # Multiple vs30 values (as floats)
    imts = ["PGA", "SA(0.5)"]  # Multiple IMT values
    aggs = ["mean", "0.005"]  # Multiple aggregation values
    poes = [0.02, 0.1]  # Multiple POE values

    # Call the function under test
    gridded_hazards = list(
        datasets.get_gridded_hazard(
            location_grid_id=location_grid_id,
            hazard_model_ids=hazard_model_ids,
            vs30s=vs30s,
            imts=imts,
            aggs=aggs,
            poes=poes,
        )
    )

    # Should return more records due to multiple parameter combinations
    assert len(gridded_hazards) > 0, "Should return gridded hazard records"

    # Check that we get combinations of the parameters
    found_combinations = set()
    for ghaz in gridded_hazards:
        combo = (ghaz.vs30, ghaz.imt, ghaz.aggr, ghaz.poe)
        found_combinations.add(combo)

        # Verify values are from our input sets
        assert ghaz.vs30 in vs30s
        assert ghaz.imt in imts
        assert ghaz.aggr in aggs
        assert ghaz.poe in poes

    print(found_combinations)

    # We should have found 8 combinations
    assert len(found_combinations) == 8, "Should find parameter combinations"


@pytest.mark.parametrize("use64bit", [True, False])
def test_get_gridded_hazard_empty_results(get_one_degree_region_grid_fixture, monkeypatch, use64bit):
    """Test get_gridded_hazard with parameters that should return no results."""
    # Setup test fixtures
    aggr_folder = Path(Path(os.path.realpath(__file__)).parent.parent, "fixtures", "aggregate_hazard")

    monkeypatch.setattr(dataset_cache, "DATASET_AGGR_URI", str(aggr_folder.absolute()))
    monkeypatch.setattr(gridded_hazard_pydantic, "DISABLE_GRIDDED_MODEL_VALIDATOR", True)
    monkeypatch.setattr(gridded_hazard_pydantic, "USE_64BIT_VALUES", use64bit)

    # Use parameters that shouldn't match any data
    location_grid_id = "NON_EXISTENT_GRID"
    hazard_model_ids = ["NSHM_v1.0.4"]
    vs30s = [400.0]  # Convert to float
    imts = ["PGA"]
    aggs = ["mean"]
    poes = [0.02]

    # Call the function under test
    gridded_hazards = list(
        datasets.get_gridded_hazard(
            location_grid_id=location_grid_id,
            hazard_model_ids=hazard_model_ids,
            vs30s=vs30s,
            imts=imts,
            aggs=aggs,
            poes=poes,
        )
    )

    # Should return empty list for non-existent location
    assert len(gridded_hazards) == 0, "Should return empty list for non-existent location grid"
