import itertools
from datetime import datetime, timezone
from pathlib import Path

import pytest
from moto import mock_dynamodb
from nzshm_common.location.coded_location import CodedLocation
from nzshm_common.location.location import LOCATIONS_BY_ID

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)

# from toshi_hazard_store.model.hazard_models_pydantic import ElasticContainerRegistryImage
from toshi_hazard_store.model.revision_4 import hazard_models  # noqa
from toshi_hazard_store.model.revision_4 import hazard_aggregate_curve, hazard_realization_curve
from toshi_hazard_store.oq_import.aws_ecr_docker_image import AwsEcrImage


@pytest.fixture
def storage_path(tmpdir_factory):
    return Path(tmpdir_factory.mktemp("hazard_storage"))


@pytest.fixture
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


######
# BELOW here will be removed once AWS pyanamodb is deprecated
#
######


# ref https://docs.pytest.org/en/7.3.x/example/parametrize.html#deferring-the-setup-of-parametrized-resources
def pytest_generate_tests(metafunc):
    if "adapted_model" in metafunc.fixturenames:
        metafunc.parametrize(
            "adapted_model",
            [
                "pynamodb",
            ],
            indirect=True,
        )


@pytest.fixture
def adapted_model(request, tmp_path):
    """This fixture reconfigures adaption of all table in the hazard_models module"""

    class AdaptedModelFixture:
        HazardRealizationCurve = None
        HazardCurveProducerConfig = None
        CompatibleHazardCalculation = None
        HazardAggregateCurve = None

    def new_model_fixture():
        model_fixture = AdaptedModelFixture()
        model_fixture.HazardRealizationCurve = globals()['hazard_realization_curve'].HazardRealizationCurve
        model_fixture.HazardCurveProducerConfig = globals()['hazard_models'].HazardCurveProducerConfig
        model_fixture.CompatibleHazardCalculation = globals()['hazard_models'].CompatibleHazardCalculation
        model_fixture.HazardAggregateCurve = globals()['hazard_aggregate_curve'].HazardAggregateCurve
        return model_fixture

    def migrate_models():
        hazard_models.migrate()
        hazard_realization_curve.migrate()
        hazard_aggregate_curve.migrate()

    def drop_models():
        hazard_models.drop_tables()
        hazard_realization_curve.drop_tables()
        hazard_aggregate_curve.drop_tables()

    if request.param == 'pynamodb':
        with mock_dynamodb():
            migrate_models()
            yield new_model_fixture()
            drop_models()

    else:
        raise ValueError("invalid internal test config")


@pytest.fixture
def many_rlz_args():
    yield dict(
        # TOSHI_ID='FAk3T0sHi1D==',
        vs30s=[250, 1500],
        imts=['PGA', 'SA(0.5)'],
        locs=[CodedLocation(o['latitude'], o['longitude'], 0.001) for o in list(LOCATIONS_BY_ID.values())[-5:]],
        sources=["c9d8be924ee7"],
        gmms=["a7d8c5d537e1"],
    )


@pytest.fixture(scope='function')
def generate_rev4_rlz_models(many_rlz_args, adapted_model):
    def model_generator():
        # values = list(map(lambda x: LevelValuePairAttribute(lvl=x / 1e3, val=(x / 1e6)), range(1, 51)))
        values = list(map(lambda x: x / 1e6, range(1, 51)))
        for loc, vs30, imt, source, gmm in itertools.product(
            many_rlz_args["locs"][:5],
            many_rlz_args["vs30s"],
            many_rlz_args["imts"],
            many_rlz_args["sources"],
            many_rlz_args["gmms"],
        ):
            yield hazard_realization_curve.HazardRealizationCurve(
                compatible_calc_fk=("A", "AA"),
                producer_config_fk=("B", "BB"),
                values=values,
                imt=imt,
                vs30=vs30,
                sources_digest=source,
                gmms_digest=gmm,
                # site_vs30=vs30,
                # hazard_solution_id=many_rlz_args["TOSHI_ID"],
                # source_tags=['TagOne'],
                # source_ids=['Z', 'XX'],
            ).set_location(loc)

    yield model_generator
