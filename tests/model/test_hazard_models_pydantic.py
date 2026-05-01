import enum
import typing
from datetime import datetime, timezone

import pyarrow as pa
import pytest

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.hazard_models_pydantic import (
    AwsEcrImage,
    CompatibleHazardCalculation,
    DisaggregationAggregate,
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


class TestDisaggregationAggregate:
    def setup_method(self):
        self.bins = {
            "mag": ["5.5", "6.5", "7.5"],
            "dist": ["10.0", "50.0", "100.0", "200.0"],
            "eps": ["-1.0", "0.0", "1.0"],
        }
        self.data = dict(
            compatible_calc_id="NZSHM22",
            hazard_model_id="NSHM_v1.0.4",
            nloc_001="-38.330~175.550",
            nloc_0="-38.0~175.0",
            imt="PGA",
            vs30=400,
            target_aggr="mean",
            probability=ProbabilityEnum._10_PCT_IN_50YRS,
            imtl=0.1,
            aggr="mean",
            bins_digest="abc123def456",
            disagg_bins=self.bins,
            disagg_values=[float(i) for i in range(3 * 4 * 3)],
        )

    def test_model_dump(self):
        model = DisaggregationAggregate(**self.data)
        expected = {**self.data, "probability": self.data["probability"].name}
        assert model.model_dump() == expected

    def test_missing_required_field(self):
        invalid = dict(**self.data)
        del invalid["bins_digest"]
        with pytest.raises(ValueError, match=r"Field required"):
            DisaggregationAggregate(**invalid)

    def test_invalid_probability_raises(self):
        invalid = dict(**self.data)
        invalid["probability"] = 999.9
        with pytest.raises(ValueError):
            DisaggregationAggregate(**invalid)

    def test_empty_bins_raises(self):
        invalid = dict(**self.data)
        invalid["disagg_bins"] = {}
        with pytest.raises(ValueError, match=r"disagg_bins must not be empty"):
            DisaggregationAggregate(**invalid)

    def test_values_shape_mismatch_raises(self):
        invalid = dict(**self.data)
        invalid["disagg_values"] = invalid["disagg_values"][:-1]
        with pytest.raises(ValueError, match=r"disagg_values length"):
            DisaggregationAggregate(**invalid)

    def test_schema_matches_pydantic_fields(self):
        """Assert that get_disagg_aggregate_schema stays in sync with DisaggregationAggregate."""

        def _strip_dict(t: pa.DataType) -> pa.DataType:
            return t.value_type if pa.types.is_dictionary(t) else t

        def _is_compatible(py_anno, arrow_type: pa.DataType) -> bool:
            a = _strip_dict(arrow_type)
            origin = typing.get_origin(py_anno)
            args = typing.get_args(py_anno)

            if py_anno is str:
                return pa.types.is_string(a) or pa.types.is_large_string(a)
            if isinstance(py_anno, type) and issubclass(py_anno, enum.Enum):
                return pa.types.is_string(a) or pa.types.is_large_string(a)
            if py_anno is int:
                return pa.types.is_integer(a)
            if py_anno is float:
                return pa.types.is_floating(a)
            if origin is list:
                return pa.types.is_list(a) and _is_compatible(args[0], a.value_type)
            if origin is dict:
                return (
                    pa.types.is_map(a)
                    and _is_compatible(args[0], a.key_type)
                    and _is_compatible(args[1], a.item_type)
                )
            raise TypeError(f"Unrecognised pydantic annotation: {py_anno!r}")

        schema = DisaggregationAggregate.pyarrow_schema()
        pydantic_fields = DisaggregationAggregate.model_fields

        assert list(pydantic_fields.keys()) == schema.names, (
            f"Field order mismatch:\n  pydantic: {list(pydantic_fields.keys())}\n  schema:   {schema.names}"
        )

        for name, field_info in pydantic_fields.items():
            arrow_field = schema.field(name)
            assert _is_compatible(field_info.annotation, arrow_field.type), (
                f"field '{name}': pydantic {field_info.annotation!r} incompatible with arrow type {arrow_field.type}"
            )
