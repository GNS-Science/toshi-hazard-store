from datetime import datetime, timezone

import pytest

from toshi_hazard_store.model.hazard_models_pydantic import (
    AwsEcrImage,
    CompatibleHazardCalculation,
    HazardCurveProducerConfig,
)


class TestCompatibleHazardCalculation:
    def setup_method(self):
        self.data = {
            "unique_id": "user_defined_unique_id",
            "notes": "Some notes about the calculation",
            "created_at": datetime.now(timezone.utc),
        }

    def test_valid_data(self):
        model = CompatibleHazardCalculation(**self.data)
        print(model)
        assert model.unique_id == self.data["unique_id"]
        assert model.notes == self.data["notes"]
        assert isinstance(model.created_at, datetime)

    def test_missing_required_field(self):
        with pytest.raises(ValueError, match="Field required"):
            del self.data["unique_id"]
            CompatibleHazardCalculation(**self.data)


class TestHazardCurveProducerConfig:
    def setup_method(self):
        ecr_image = AwsEcrImage(
            registryId='ABC',
            repositoryName='123',
            imageDigest="sha256:abcdef1234567890",
            imageTags=["tag1"],
            imagePushedAt="2023-03-20T09:02:35.314495+00:00",
            lastRecordedPullTime="2023-03-20T09:02:35.314495+00:00",
            imageSizeInBytes=123,
            imageManifestMediaType='json',
            artifactMediaType='blob',
        )
        self.data = {
            "unique_id": "user_defined_unique_id",
            "compatible_calc_fk": "some_compatible_calc_id",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "ecr_image": ecr_image.model_dump(),
            "ecr_image_digest": ecr_image.imageDigest,
            "config_digest": "hash_value",
            "notes": "Some additional notes",
        }

    def test_valid_data(self):
        model = HazardCurveProducerConfig(**self.data)
        assert model.unique_id == self.data["unique_id"]
        assert model.compatible_calc_fk == self.data["compatible_calc_fk"]
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

        print(model.model_dump_json(indent=2))
        # assert 0

    def test_missing_required_field(self):
        with pytest.raises(ValueError, match=r"Field required"):
            del self.data["config_digest"]
            HazardCurveProducerConfig(**self.data)
