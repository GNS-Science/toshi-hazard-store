"""
# Test Expansion for Hazard Models Manager

These tests cover the following key areas:

1. Error handling for invalid parameters
2. Error handling for invalid types
3. Handling duplicate IDs
4. Handling non-existent IDs for loading, updating, and deleting
5. Creating models using model instances instead of dictionaries
6. Referential integrity checking during creation and updates
7. Handling corrupted JSON data

The added tests provide comprehensive coverage of the error paths and edge cases in the code,
 complementing the existing tests which already cover the happy paths.
"""

import pytest
from pydantic import ValidationError

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.model.hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig

# =====================================
# Additional Tests for CompatibleHazardCalculationManager
# =====================================


def test_compatible_hazard_calculation_create_invalid_parameters(storage_path):
    """Test creating a compatible hazard calculation with invalid parameters."""
    manager = CompatibleHazardCalculationManager(storage_path)

    # Missing required field
    invalid_data = {"notes": "Test notes"}
    with pytest.raises(ValueError):
        manager.create(invalid_data)


def test_compatible_hazard_calculation_create_invalid_type(storage_path):
    """Test creating a compatible hazard calculation with an invalid type."""
    manager = CompatibleHazardCalculationManager(storage_path)

    # Not a dict or CompatibleHazardCalculation instance
    with pytest.raises(TypeError):
        manager.create("not_a_dict_or_model")


def test_compatible_hazard_calculation_create_existing_id(storage_path):
    """Test creating a compatible hazard calculation with an ID that already exists."""
    manager = CompatibleHazardCalculationManager(storage_path)

    data = {"unique_id": "duplicate_id", "notes": "Original entry"}
    manager.create(data)

    # Try to create with the same ID
    data2 = {"unique_id": "duplicate_id", "notes": "Duplicate entry"}
    with pytest.raises(FileExistsError):
        manager.create(data2)


def test_compatible_hazard_calculation_load_nonexistent(storage_path):
    """Test loading a compatible hazard calculation that doesn't exist."""
    manager = CompatibleHazardCalculationManager(storage_path)

    with pytest.raises(FileNotFoundError):
        manager.load("nonexistent_id")


def test_compatible_hazard_calculation_update_nonexistent(storage_path):
    """Test updating a compatible hazard calculation that doesn't exist."""
    manager = CompatibleHazardCalculationManager(storage_path)

    with pytest.raises(FileNotFoundError):
        manager.update("nonexistent_id", {"notes": "Updated notes"})


def test_compatible_hazard_calculation_delete_nonexistent(storage_path):
    """Test deleting a compatible hazard calculation that doesn't exist."""
    manager = CompatibleHazardCalculationManager(storage_path)

    # Should not raise an error, deleting non-existent is handled gracefully
    manager.delete("nonexistent_id")


def test_compatible_hazard_calculation_with_instance(storage_path):
    """Test creating a compatible hazard calculation with a model instance."""
    manager = CompatibleHazardCalculationManager(storage_path)

    model = CompatibleHazardCalculation(unique_id="model_instance_id")
    manager.create(model)

    loaded = manager.load("model_instance_id")
    assert loaded.unique_id == "model_instance_id"


# =====================================
# Additional Tests for HazardCurveProducerConfigManager
# =====================================


def test_hazard_curve_producer_config_create_invalid_parameters(storage_path, ch_manager):
    """Test creating a hazard curve producer config with invalid parameters."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Missing required fields
    invalid_data = {"unique_id": "invalid_hcp", "compatible_calc_fk": "chc1"}
    with pytest.raises(ValueError):
        manager.create(invalid_data)


def test_hazard_curve_producer_config_create_invalid_type(storage_path, ch_manager):
    """Test creating a hazard curve producer config with an invalid type."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Not a dict or HazardCurveProducerConfig instance
    with pytest.raises(TypeError):
        manager.create("not_a_dict_or_model")


def test_hazard_curve_producer_config_create_existing_id(storage_path, ch_manager, compatible_hazard_calc_data):
    """Test creating a hazard curve producer config with an ID that already exists."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Create a valid HazardCurveProducerConfig first

    fake_ecr_image_str = "sha256:Image0123"

    data = {
        "compatible_calc_fk": compatible_hazard_calc_data["unique_id"],
        "configuration_hash": "hash1",
        "ecr_image_digest": fake_ecr_image_str,
        "config_digest": "hash_digest",
        "notes": "Some additional notes",
    }

    manager.create(data)

    # Try to create with the same ID
    data2 = {
        "compatible_calc_fk": compatible_hazard_calc_data["unique_id"],
        "configuration_hash": "hash1",
        "ecr_image_digest": fake_ecr_image_str,
        "config_digest": "hash_digest",
        "notes": "Some additional notes",
    }
    with pytest.raises(FileExistsError):
        manager.create(data2)


def test_hazard_curve_producer_config_load_nonexistent(storage_path, ch_manager):
    """Test loading a hazard curve producer config that doesn't exist."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    with pytest.raises(FileNotFoundError):
        manager.load("nonexistent_hcp_id")


def test_hazard_curve_producer_config_update_nonexistent(storage_path, ch_manager):
    """Test updating a hazard curve producer config that doesn't exist."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    with pytest.raises(FileNotFoundError):
        manager.update("nonexistent_hcp_id", {"producer_software": "updated_software"})


def test_hazard_curve_producer_config_delete_nonexistent(storage_path, ch_manager):
    """Test deleting a hazard curve producer config that doesn't exist."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Should not raise an error, deleting non-existent is handled gracefully
    manager.delete("nonexistent_hcp_id")


def test_hazard_curve_producer_config_with_instance(storage_path, ch_manager, compatible_hazard_calc_data):
    """Test creating a hazard curve producer config with a model instance."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    model = HazardCurveProducerConfig(
        # unique_id="model_hcp_instance_id",
        compatible_calc_fk=compatible_hazard_calc_data["unique_id"],
        ecr_image_digest="sha256:Image0123",
        config_digest="test_hash",
    )
    manager.create(model)

    loaded = manager.load("Image0123")
    assert loaded.unique_id == "Image0123"


def test_hazard_curve_producer_config_referential_integrity_create(storage_path, ch_manager):
    """Test referential integrity check when creating a hazard curve producer config."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Try to create with a non-existent compatible_calc_fk
    data = {
        # "unique_id": "ref_integrity_test",
        "compatible_calc_fk": "non_existent_chc_id",
        "configuration_hash": "hash1",
        "ecr_image_digest": "sha256:Image0123",
        "config_digest": "hash_digest",
        "notes": "Some additional notes",
    }
    with pytest.raises(ValueError):
        manager.create(data)


def test_hazard_curve_producer_config_referential_integrity_update(
    storage_path, ch_manager, compatible_hazard_calc_data
):
    """Test referential integrity check when updating a hazard curve producer config."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Create a valid config
    data = {
        # "unique_id": "ref_integrity_update_test",
        "compatible_calc_fk": compatible_hazard_calc_data["unique_id"],
        "configuration_hash": "hash1",
        "ecr_image_digest": "sha256:ref_integrity_update_test",
        "config_digest": "hash_digest",
        "notes": "Some additional notes",
    }
    manager.create(data)

    # Try to update with a non-existent compatible_calc_fk
    with pytest.raises(ValueError):
        manager.update("ref_integrity_update_test", {"compatible_calc_fk": "non_existent_chc_id"})


def test_hazard_curve_producer_config_loading_broken_json(
    storage_path, ch_manager, compatible_hazard_calc_data, monkeypatch
):
    """Test loading a hazard curve producer config with invalid JSON."""
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Write invalid JSON to the file
    file_path = manager._get_path("broken_json_test")
    with open(file_path, 'w') as f:
        f.write("This is not valid JSON")

    # This should raise a JSONDecodeError, which Pydantic will catch and raise its own error
    with pytest.raises(ValidationError):
        manager.load("broken_json_test")
