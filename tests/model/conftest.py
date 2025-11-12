from datetime import datetime, timezone
from pathlib import Path

import pytest

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.oq_import.aws_ecr_docker_image import AwsEcrImage


@pytest.fixture
def storage_path(tmpdir_factory):
    return Path(tmpdir_factory.mktemp("hazard_storage"))


@pytest.fixture(scope='session')
def compatible_hazard_calc_data():
    now = datetime.now(timezone.utc)
    return {"unique_id": "chc1", "created_at": now, "updated_at": now}


@pytest.fixture
def hazard_curve_producer_config_data(compatible_hazard_calc_data):
    now = datetime.now(timezone.utc)

    ecr_image = AwsEcrImage(
        registryId='ABC',
        repositoryName='123',
        imageDigest="sha256:ImageDigest1234567890",
        imageTags=["tag1"],
        imagePushedAt="2023-03-20T09:02:35.314495+00:00",
        lastRecordedPullTime="2023-03-20T09:02:35.314495+00:00",
        imageSizeInBytes=123,
        imageManifestMediaType='json',
        artifactMediaType='blob',
    )

    return {
        "compatible_calc_fk": compatible_hazard_calc_data["unique_id"],
        "created_at": now,
        "updated_at": now,
        "ecr_image": ecr_image.model_dump(),
        "ecr_image_digest": ecr_image.imageDigest,
        "config_digest": "hash_value",
        "notes": "Some additional notes",
    }


@pytest.fixture
def ch_manager(storage_path, compatible_hazard_calc_data):
    manager = CompatibleHazardCalculationManager(storage_path)
    manager.create(compatible_hazard_calc_data)
    return manager


@pytest.fixture
def hcp_manager(storage_path, hazard_curve_producer_config_data, compatible_hazard_calc_data):
    ch_manager = CompatibleHazardCalculationManager(storage_path)
    ch_manager.create(compatible_hazard_calc_data)
    assert ch_manager.get_all_ids()
    manager = HazardCurveProducerConfigManager(storage_path, ch_manager)
    manager.create(hazard_curve_producer_config_data)
    return manager
