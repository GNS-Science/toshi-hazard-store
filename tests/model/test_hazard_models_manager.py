from datetime import datetime, timezone

import pytest

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.model.hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig


def test_compatible_hazard_calculation_create(ch_manager, compatible_hazard_calc_data):
    chc = ch_manager.load(compatible_hazard_calc_data["unique_id"])
    assert isinstance(chc, CompatibleHazardCalculation)


def test_compatible_hazard_calculation_get_all_ids(ch_manager, compatible_hazard_calc_data):
    all_ids = ch_manager.get_all_ids()
    assert compatible_hazard_calc_data["unique_id"] in all_ids


def test_compatible_hazard_calculation_round_trip(storage_path):
    manager = CompatibleHazardCalculationManager(storage_path)
    now = datetime.now(timezone.utc)
    new_data = {"unique_id": "chc1-round-trip", "created_at": now, "updated_at": now}
    manager.create(new_data)
    rehydrated = manager.load(new_data["unique_id"])
    print(rehydrated)
    assert rehydrated == CompatibleHazardCalculation(**new_data)


def test_compatible_hazard_calculation_update(ch_manager, compatible_hazard_calc_data):
    new_updated_at = datetime.now(timezone.utc)
    data_to_update = {"updated_at": new_updated_at.isoformat()}
    ch_manager.update(compatible_hazard_calc_data["unique_id"], data_to_update)

    chc = ch_manager.load(compatible_hazard_calc_data["unique_id"])
    assert chc.updated_at == new_updated_at


def test_compatible_hazard_calculation_delete(ch_manager, compatible_hazard_calc_data):
    unique_id = compatible_hazard_calc_data["unique_id"]
    ch_manager.delete(unique_id)
    with pytest.raises(FileNotFoundError):
        ch_manager.load(unique_id)


################
# hazard_curve_producer_config tests
################


def test_hazard_curve_producer_config_create(hcp_manager, hazard_curve_producer_config_data):
    hcp = hcp_manager.load(hazard_curve_producer_config_data["unique_id"])
    assert isinstance(hcp, HazardCurveProducerConfig)


def test_hazard_curve_producer_config_update(hcp_manager, hazard_curve_producer_config_data):
    new_updated_at = datetime.now(timezone.utc)
    data_to_update = {"updated_at": new_updated_at.isoformat()}
    hcp_manager.update(hazard_curve_producer_config_data["unique_id"], data_to_update)

    hcp = hcp_manager.load(hazard_curve_producer_config_data["unique_id"])
    assert hcp.updated_at == new_updated_at


def test_hazard_curve_producer_config_delete(hcp_manager, hazard_curve_producer_config_data):
    unique_id = hazard_curve_producer_config_data["unique_id"]
    hcp_manager.delete(unique_id)
    with pytest.raises(FileNotFoundError):
        hcp_manager.load(unique_id)


@pytest.mark.skip('WIP')
def test_referential_integrity_failure(
    ch_manager, storage_path, compatible_hazard_calc_data, hazard_curve_producer_config_data
):
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # CBC this is the wrong approach - shoudl probably mock ch_manager get_all_ids method instead
    # Attempt to create a config without the referenced CompatibleHazardCalculation existing
    with pytest.raises(ValueError) as exc_info:
        del hazard_curve_producer_config_data["compatible_calc_fk"]
        manager.create(hazard_curve_producer_config_data)

    assert "Referenced compatible hazard calculation does not exist" in str(exc_info.value)


@pytest.mark.skip('WIP')
def test_referential_integrity_update_failure(
    storage_path, ch_manager, compatible_hazard_calc_data, hazard_curve_producer_config_data
):
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)

    # Create a valid config
    hcp_id = hazard_curve_producer_config_data["unique_id"]
    del hazard_curve_producer_config_data["compatible_calc_fk"]  # Remove to create without ref

    invalid_ref_hcp_data = hazard_curve_producer_config_data.copy()
    invalid_ref_hcp_data.update({"unique_id": "hcp2", "compatible_calc_fk": "non_existent_chc"})

    manager.create(invalid_ref_hcp_data)

    # Attempt to update the config with a non-existent reference
    with pytest.raises(ValueError) as exc_info:
        data_to_update = {"compatible_calc_fk": "another_non_existent_chc"}
        manager.update(hcp_id, data_to_update)

    assert "Referenced compatible hazard calculation does not exist" in str(exc_info.value)
