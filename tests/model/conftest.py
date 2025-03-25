from datetime import datetime, timezone
from pathlib import Path

import pytest

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)


@pytest.fixture(scope="session")
def storage_path(tmpdir_factory):
    return Path(tmpdir_factory.mktemp("hazard_storage"))


@pytest.fixture(scope='session')
def compatible_hazard_calc_data():
    now = datetime.now(timezone.utc)
    return {"unique_id": "chc1", "created_at": now, "updated_at": now}


@pytest.fixture(scope='session')
def hazard_curve_producer_config_data(compatible_hazard_calc_data):
    now = datetime.now(timezone.utc)
    return {
        "unique_id": "hcp1",
        "compatible_calc_fk": compatible_hazard_calc_data["unique_id"],
        "created_at": now,
        "updated_at": now,
        "effective_from": None,
        "last_used": None,
        "tags": ["tag1", "tag2"],
        "producer_software": "software_name",
        "producer_version_id": "version_1.0",
        "configuration_hash": "hash_value",
        "configuration_data": "{\"key\": \"value\"}",
        "imts": ["PGA", "SA(1.0)"],
        "imt_levels": [0.1, 0.2],
        "notes": "Some additional notes",
    }


@pytest.fixture(scope='session')
def ch_manager(storage_path, compatible_hazard_calc_data):
    manager = CompatibleHazardCalculationManager(storage_path)
    manager.create(compatible_hazard_calc_data)
    return manager


@pytest.fixture(scope='session')
def hcp_manager(storage_path, hazard_curve_producer_config_data, compatible_hazard_calc_data):
    ch_manager = CompatibleHazardCalculationManager(storage_path)
    ch_manager.create(compatible_hazard_calc_data)
    assert ch_manager.get_all_ids()
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)
    manager.create(hazard_curve_producer_config_data)
    return manager
