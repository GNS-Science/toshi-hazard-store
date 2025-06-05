from datetime import datetime, timezone

import pytest

from toshi_hazard_store.model.hazard_models_pydantic import (
    AwsEcrImage,
    CompatibleHazardCalculation,
    HazardAggregateCurve,
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
        assert model.unique_id == self.data["ecr_image_digest"][7:]
        assert model.compatible_calc_fk == self.data["compatible_calc_fk"]
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

        print(model.model_dump_json(indent=2))
        # assert 0

    def test_missing_required_field(self):
        with pytest.raises(ValueError, match=r"Field required"):
            del self.data["config_digest"]
            HazardCurveProducerConfig(**self.data)


class TestHazardAggregateCurve:
    def setup_method(self):
        self.data = dict(
            compatible_calc_id="NZSHM22",
            hazard_model_id="MyNewModel",
            nloc_001="-100.100~45.045",
            nloc_0="-100.0~45.0",
            imt="PGA",
            vs30=1000,
            aggr="mean",
            values=[(x / 1000) for x in range(44)],
        )

    def test_model_dump(self):
        model = HazardAggregateCurve(**self.data)
        assert model.model_dump() == self.data

    def test_wrong_value_raises(self):
        invalid_data = dict(**self.data)
        print(invalid_data)

        invalid_data["values"] = invalid_data["values"][:-1]
        with pytest.raises(ValueError, match=r"expected 44 values but") as exc:
            HazardAggregateCurve(**invalid_data)
        print(exc)
