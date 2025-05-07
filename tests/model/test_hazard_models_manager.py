import pathlib
from datetime import datetime, timezone

import pytest

from toshi_hazard_store.model.hazard_models_manager import CompatibleHazardCalculationManager
from toshi_hazard_store.model.hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig


def test_reuse_existing_storage_folder(ch_manager, storage_path):
    # ch_manger will have created the storage folder ...
    cm2 = CompatibleHazardCalculationManager(storage_path)
    assert cm2.storage_folder == ch_manager.storage_folder


def test_non_existing_storage_folder_raises():
    storage_path = pathlib.Path("Some_nonsense/path")
    with pytest.raises(ValueError) as exc_info:
        _ = CompatibleHazardCalculationManager(storage_path)
    assert f"'{storage_path}' is not a valid path for storage_folder." in str(exc_info.value)


def test_compatible_hazard_calculation_create_load(ch_manager, compatible_hazard_calc_data):
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


def test_compatible_hazard_calculation_update_sans_updated_at(ch_manager, compatible_hazard_calc_data):
    notes = "Urbis dolur"
    data_to_update = {"notes": notes}
    ch_manager.update(compatible_hazard_calc_data["unique_id"], data_to_update)

    chc = ch_manager.load(compatible_hazard_calc_data["unique_id"])
    assert chc.notes == notes
    assert chc.updated_at > compatible_hazard_calc_data["updated_at"]


def test_compatible_hazard_calculation_delete(ch_manager, compatible_hazard_calc_data):
    unique_id = compatible_hazard_calc_data["unique_id"]
    ch_manager.delete(unique_id)
    with pytest.raises(FileNotFoundError):
        ch_manager.load(unique_id)


################
# hazard_curve_producer_config tests
################


def test_hazard_curve_producer_config_create_load(hcp_manager, hazard_curve_producer_config_data):
    hcp = hcp_manager.load("ImageDigest1234567890")
    assert isinstance(hcp, HazardCurveProducerConfig)


def test_hazard_curve_producer_config_update(hcp_manager, hazard_curve_producer_config_data):
    new_updated_at = datetime.now(timezone.utc)
    data_to_update = {"updated_at": new_updated_at.isoformat()}
    hcp_manager.update("ImageDigest1234567890", data_to_update)

    hcp = hcp_manager.load("ImageDigest1234567890")
    assert hcp.updated_at == new_updated_at


def test_hazard_curve_producer_config_delete(hcp_manager, hazard_curve_producer_config_data):
    unique_id = "ImageDigest1234567890"
    hcp_manager.delete(unique_id)
    with pytest.raises(FileNotFoundError):
        hcp_manager.load(unique_id)


def test_referential_integrity_load_failure(hcp_manager, hazard_curve_producer_config_data, monkeypatch):
    monkeypatch.setattr(hcp_manager.ch_manager, 'get_all_ids', lambda: [])

    hcp_id = "ImageDigest1234567890"
    with pytest.raises(ValueError) as exc_info:
        _ = hcp_manager.load(hcp_id)
    assert "Referenced compatible hazard calculation" in str(exc_info.value)
