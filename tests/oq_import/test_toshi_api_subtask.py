import pathlib
from unittest import mock

import pytest

import toshi_hazard_store.model.hazard_models_manager as hazard_models_manager
from toshi_hazard_store.oq_import import oq_config, toshi_api_subtask
from toshi_hazard_store.oq_import.aws_ecr_docker_image import AwsEcrImage
from toshi_hazard_store.oq_import.toshi_api_subtask import (
    SubtaskRecord,
    build_producers,
    build_realisations,
    generate_subtasks,
)


# Mocks and fixtures
@pytest.fixture
def mock_gtapi(task_id):
    class MockApiClient:
        def get_gt_subtasks(self, id):
            return {
                "children": {
                    "edges": [
                        {"node": {"child": {"id": "task_id_1"}}},
                        {"node": {"child": {"id": "task_id_2"}}},
                    ]
                }
            }

        def get_oq_hazard_task(self, id):
            return {
                "created": "2023-03-20T09:02:35.314495+00:00",
                "hazard_solution": {
                    "id": task_id,
                    "hdf5_archive": {
                        "file_name": "A file.zip",
                        "file_url": "https://a_file",
                    },
                },
            }

    return MockApiClient()


@pytest.fixture
def mock_subtask_info(task_id, general_task_id, hdf5_calc_fixture):
    return SubtaskRecord(
        gt_id=general_task_id,
        hazard_calc_id=task_id,
        config_hash="config_hash_1",
        ecr_image=AwsEcrImage(
            registryId='ABC',
            repositoryName='123',
            imageDigest="sha256:abcdef1234567890",
            imageTags=["tag1"],
            imagePushedAt="2023-03-20T09:02:35.314495+00:00",
            lastRecordedPullTime="2023-03-20T09:02:35.314495+00:00",
            imageSizeInBytes=123,
            imageManifestMediaType='json',
            artifactMediaType='blob',
        ),
        hdf5_path=hdf5_calc_fixture,
        vs30=275,
    )


@pytest.fixture
def mock_compatible_calc():
    class MockCompatibleHazardCalculation:
        unique_id = "compatible_calc_1"

    return MockCompatibleHazardCalculation()


@pytest.fixture
def mock_hazard_producer_config():
    class MockHazardCurveProducerConfig:
        unique_id = "hpc_id"

    return MockHazardCurveProducerConfig()


# Tests for build_producers


@pytest.mark.parametrize("verbose", [True, False])
@pytest.mark.parametrize("update", [False, True])
def test_build_producers_existing_config(mock_subtask_info, mock_compatible_calc, monkeypatch, verbose, update):
    # hpc_manager_load = mock.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.load')
    # hpc_manager_update = mock.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.update')

    mock_hpc = mock.MagicMock(hazard_models_manager.HazardCurveProducerConfigManager)
    monkeypatch.setattr(toshi_api_subtask, "hpc_manager", mock_hpc)

    build_producers(mock_subtask_info, mock_compatible_calc, verbose=verbose, update=update)

    mock_hpc.return_value.load.return_value.assert_called


@pytest.mark.parametrize("verbose", [True, False])
@pytest.mark.parametrize("update", [False, True])
def test_build_producers_new_config(
    mock_subtask_info, mock_compatible_calc, mock_hazard_producer_config, tmpdir_factory, monkeypatch, verbose, update
):

    mock_hpc = mock.MagicMock(hazard_models_manager.HazardCurveProducerConfigManager)
    monkeypatch.setattr(toshi_api_subtask, "hpc_manager", mock_hpc)

    build_producers(mock_subtask_info, mock_compatible_calc, verbose=verbose, update=update)

    mock_hpc.return_value.load.assert_called
    mock_hpc.return_value.create.assert_called_once


# Tests for build_realisations
@pytest.mark.parametrize("verbose", [True, False])
def test_build_realisations(
    mock_subtask_info, mock_compatible_calc, mock_hazard_producer_config, tmpdir_factory, monkeypatch, verbose
):

    mock_hpc = mock.MagicMock(hazard_models_manager.HazardCurveProducerConfigManager)
    # mock_hpc.return_value.load = lambda id: mock_hazard_producer_config

    monkeypatch.setattr(toshi_api_subtask, "hpc_manager", mock_hpc)
    monkeypatch.setattr(mock_hpc, 'load', lambda id: mock_hazard_producer_config)

    output_folder = pathlib.Path(tmpdir_factory.mktemp("build_realisations"))

    build_realisations(mock_subtask_info, mock_compatible_calc.unique_id, output=str(output_folder), verbose=verbose)

    partitions = list(output_folder.glob("nloc_0*"))
    assert len(partitions) == 4  # this calc create 4 nloc_0 partitions

    # assert mocker.assert_called_once


# Tests for generate_subtasks
@pytest.mark.parametrize("verbose", [True, False])
@pytest.mark.parametrize("with_rlzs", [False, True])
def test_generate_subtasks(
    task_id,
    general_task_id,
    mock_gtapi,
    monkeypatch,
    solution_archive_fixture,
    mock_task_args_file_path,
    verbose,
    with_rlzs,
):
    work_folder = mock_task_args_file_path.parent.parent.parent.parent
    mock_ecr_images = [{"imageDigest": "sha256:abcdef1234567890"}]

    mock_ecr = mock.MagicMock(toshi_api_subtask.aws_ecr.ECRRepoStash)
    mock_ecr.return_value.active_image_asat.return_value = mock_ecr_images[0]

    monkeypatch.setattr(toshi_api_subtask.aws_ecr.ECRRepoStash, 'fetch', lambda *args, **kwargs: mock_ecr)

    monkeypatch.setattr(oq_config, 'download_artefacts', lambda *args, **kwargs: None)
    monkeypatch.setattr(oq_config, '_save_api_file', lambda *args, **kwargs: solution_archive_fixture)

    subtasks = list(
        generate_subtasks(general_task_id, mock_gtapi, [task_id], work_folder, with_rlzs=with_rlzs, verbose=verbose)
    )

    mock_ecr.return_value.active_image_asat.assert_called_once
    assert len(subtasks) == 1
    assert isinstance(subtasks[0], SubtaskRecord)
    assert subtasks[0].vs30 == '760'
