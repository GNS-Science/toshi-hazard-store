import hashlib
from typing import Iterator

import pytest
from toshi_hazard_store.oq_import.toshi_api_subtask import (
    SubtaskRecord,
    ProducerConfigKey,
    build_producers,
    build_realisations,
    generate_subtasks,
)

# Mocks and fixtures
@pytest.fixture
def mock_gtapi(mocker):
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
                "hazard_solution": {"id": "hazard_calc_id_1"},
            }

    return MockApiClient()

@pytest.fixture
def mock_subtask_info():
    return SubtaskRecord(
        gt_id="gt_id_1",
        hazard_calc_id="hazard_calc_id_1",
        config_hash="config_hash_1",
        image={"imageDigest": "sha256:abcdef1234567890", "imageTags": ["tag1"], "imagePushedAt": "2023-03-20T09:02:35.314495+00:00", "lastRecordedPullTime": "2023-03-20T09:02:35.314495+00:00"},
        hdf5_path="path/to/hdf5",
        vs30=275,
    )

@pytest.fixture
def mock_compatible_calc():
    class MockCompatibleHazardCalculation:
        unique_id = "compatible_calc_1"
    return MockCompatibleHazardCalculation()

# Tests for build_producers
def test_build_producers_existing_config(mock_subtask_info, mock_compatible_calc, mocker):
    hpc_manager_load = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.load')
    hpc_manager_update = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.update')

    # Mock existing producer config
    mock_producer_config = {"unique_id": "existing_config_1"}
    hpc_manager_load.return_value = mock_producer_config

    build_producers(mock_subtask_info, mock_compatible_calc, verbose=True, update=True)

    hpc_manager_update.assert_called_once_with("existing_config_1", mock_producer_config.model_dump())

def test_build_producers_new_config(mock_subtask_info, mock_compatible_calc, mocker):
    hpc_manager_load = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.load', side_effect=FileNotFoundError)
    hpc_manager_create = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.create')

    build_producers(mock_subtask_info, mock_compatible_calc, verbose=True, update=False)

    expected_config = {
        "unique_id": hashlib.md5(str(ProducerConfigKey("461564345538.dkr.ecr.us-east-1.amazonaws.com/nzshm22/runzi-openquake", "abcdef1234567890", "config_hash_1")).encode()).hexdigest(),
        "compatible_calc_fk": "compatible_calc_1",
        "tags": ["tag1"],
        "effective_from": "2023-03-20T09:02:35.314495+00:00",
        "last_used": "2023-03-20T09:02:35.314495+00:00",
        "producer_software": "461564345538.dkr.ecr.us-east-1.amazonaws.com/nzshm22/runzi-openquake",
        "producer_version_id": "abcdef1234567890",
        "configuration_hash": "config_hash_1",
        "notes": "notes"
    }
    hpc_manager_create.assert_called_once_with(expected_config)

# Tests for build_realisations
def test_build_realisations(mock_subtask_info, mock_compatible_calc, mocker):
    append_models_to_dataset = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.pyarrow_dataset.append_models_to_dataset')

    build_realisations(mock_subtask_info, mock_compatible_calc, output_folder="path/to/output", verbose=True)

    append_models_to_dataset.assert_called_once()

# Tests for generate_subtasks
def test_generate_subtasks(mock_gtapi, mock_subtask_info, mocker):
    hpc_manager_load = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.hpc_manager.load')
    ecr_repo_stash_fetch = mocker.patch('toshi_hazard_store.oq_import.toshi_api_subtask.aws_ecr.ECRRepoStash.fetch')

    # Mock ECR stash
    mock_ecr_images = [{"imageDigest": "sha256:abcdef1234567890"}]
    ecr_repo_stash_fetch.return_value = mock_ecr_images

    subtasks = list(generate_subtasks("gt_id_1", mock_gtapi, ["task_id_1"], "path/to/work", with_rlzs=True, verbose=True))

    assert len(subtasks) == 1
    assert isinstance(subtasks[0], SubtaskRecord)
