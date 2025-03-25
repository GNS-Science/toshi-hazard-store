from datetime import datetime, timezone

import pytest

from toshi_hazard_store.model.hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig


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
        self.data = {
            "unique_id": "user_defined_unique_id",
            "compatible_calc_fk": "some_compatible_calc_id",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
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

    def test_valid_data(self):
        model = HazardCurveProducerConfig(**self.data)
        assert model.unique_id == self.data["unique_id"]
        assert model.compatible_calc_fk == self.data["compatible_calc_fk"]
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

    def test_missing_required_field(self):
        with pytest.raises(ValueError, match=r"Field required"):
            del self.data["producer_software"]
            HazardCurveProducerConfig(**self.data)
