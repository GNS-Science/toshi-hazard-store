from datetime import datetime, timezone

import pytest

from toshi_hazard_store.model.hazard_models_pydantic import (
    CompatibleHazardCalculation,
    ElasticContainerRegistryImage,
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
        ecr_image = ElasticContainerRegistryImage(
            image_uri='461564345538...runzi-ffc9af8_nz_openquake-3-19-0_patch_v2',
            image_digest='sha256:e8b44b806570dcdc4a725cafc2fbaf6dae99dbfbe69345d86b3069d3fe4a2bc6',
            tags=['runzi-ffc9af8_nz_openquake-3-19-0_patch_v2'],
            pushed_at=datetime.fromisoformat("2024-10-24T14:07:02+12:00"),
            last_pulled_at=datetime.fromisoformat("2024-10-24T14:10:56+12:00"),
        )

        self.data = {
            "unique_id": "user_defined_unique_id",
            "compatible_calc_fk": "some_compatible_calc_id",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "ecr_image": ecr_image.model_dump(),
            "ecr_image_digest": ecr_image.image_hash_digest(),
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
