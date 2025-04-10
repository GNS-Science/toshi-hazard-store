import hashlib
import pathlib
from unittest import mock

import pytest

from toshi_hazard_store.oq_import import oq_config, toshi_api_subtask
from toshi_hazard_store.oq_import.toshi_api_subtask import (
    ProducerConfigKey,
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
        image={
            "imageDigest": "sha256:abcdef1234567890",
            "imageTags": ["tag1"],
            "imagePushedAt": "2023-03-20T09:02:35.314495+00:00",
            "lastRecordedPullTime": "2023-03-20T09:02:35.314495+00:00",
        },
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
@pytest.mark.skip("WIP")
def test_build_producers_existing_config(mock_subtask_info, mock_compatible_calc, mocker):
    hpc_manager_load = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.load')
    hpc_manager_update = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.update')

    # Mock existing producer config
    mock_producer_config = {"unique_id": "existing_config_1"}
    hpc_manager_load.return_value = mock_producer_config

    build_producers(mock_subtask_info, mock_compatible_calc, verbose=True, update=True)

    hpc_manager_update.assert_called_once_with("existing_config_1", mock_producer_config.model_dump())


@pytest.mark.skip("WIP")
def test_build_producers_new_config(mock_subtask_info, mock_compatible_calc, mocker):
    # hpc_manager_load = mocker.patch(
    #     'toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.load', side_effect=FileNotFoundError
    # )
    hpc_manager_create = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.create')

    build_producers(mock_subtask_info, mock_compatible_calc, verbose=True, update=False)

    expected_config = {
        "unique_id": hashlib.md5(
            str(
                ProducerConfigKey(
                    "461564345538.dkr.ecr.us-east-1.amazonaws.com/nzshm22/runzi-openquake",
                    "abcdef1234567890",
                    "config_hash_1",
                )
            ).encode()
        ).hexdigest(),
        "compatible_calc_fk": "compatible_calc_1",
        "tags": ["tag1"],
        "effective_from": "2023-03-20T09:02:35.314495+00:00",
        "last_used": "2023-03-20T09:02:35.314495+00:00",
        "producer_software": "461564345538.dkr.ecr.us-east-1.amazonaws.com/nzshm22/runzi-openquake",
        "producer_version_id": "abcdef1234567890",
        "configuration_hash": "config_hash_1",
        "notes": "notes",
    }
    hpc_manager_create.assert_called_once_with(expected_config)


# Tests for build_realisations
def test_build_realisations(
    mock_subtask_info, mock_compatible_calc, mock_hazard_producer_config, tmpdir_factory, monkeypatch
):

    # mocker = mock.Mock()
    # monkeypatch.setattr(toshi_api_subtask.pyarrow_dataset, "append_models_to_dataset", mocker)
    monkeypatch.setattr(toshi_api_subtask.hpc_manager, 'load', lambda id: mock_hazard_producer_config)

    output_folder = pathlib.Path(tmpdir_factory.mktemp("build_realisations"))

    build_realisations(mock_subtask_info, mock_compatible_calc, output_folder=output_folder, verbose=True)

    partitions = list(output_folder.glob("nloc_0*"))
    assert len(partitions) == 4  # this calc create 4 nloc_0 partitions

    # assert mocker.assert_called_once


# Tests for generate_subtasks
# TODO: rework mocking ... this is slow
@pytest.mark.parametrize("verbose", [True, False])
@pytest.mark.parametrize("with_rlzs", [True, False])
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
    # hpc_manager_load = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.load')

    ecr_repo_stash_fetch = mock.patch('toshi_hazard_store.oq_import.toshi_api_subtask.aws_ecr.ECRRepoStash.fetch')
    mock_ecr_images = [{"imageDigest": "sha256:abcdef1234567890"}]
    ecr_repo_stash_fetch.return_value = mock_ecr_images

    work_folder = mock_task_args_file_path.parent.parent.parent.parent

    monkeypatch.setattr(oq_config, 'download_artefacts', lambda *args, **kwargs: None)
    monkeypatch.setattr(oq_config, '_save_api_file', lambda *args, **kwargs: solution_archive_fixture)

    subtasks = list(
        generate_subtasks(general_task_id, mock_gtapi, [task_id], work_folder, with_rlzs=with_rlzs, verbose=verbose)
    )

    assert len(subtasks) == 1
    assert isinstance(subtasks[0], SubtaskRecord)
    assert subtasks[0].vs30 == '760'
