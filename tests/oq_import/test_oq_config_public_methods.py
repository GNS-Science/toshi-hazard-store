from unittest.mock import MagicMock, patch

import pytest

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.model.hazard_models_pydantic import HazardCurveProducerConfig
from toshi_hazard_store.oq_import import oq_config


# Mocking the API client and other dependencies
@pytest.fixture
def mock_gtapi():
    with patch('toshi_hazard_store.oq_import.toshi_api_client.ApiClient') as mock:
        yield mock.return_value


@pytest.fixture
def mock_chc_manager():
    return CompatibleHazardCalculationManager(pathlib.Path('/mock/storage_folder'))


@pytest.fixture
def mock_hpc_manager(mock_chc_manager):
    return HazardCurveProducerConfigManager(pathlib.Path('/mock/storage_folder'), mock_chc_manager)


# Test cases for oq_config functions


def test_download_artefacts(mock_gtapi, tmp_path):
    subtasks_folder = tmp_path / 'subtasks'
    subtasks_folder.mkdir()
    task_id = '12345'
    hazard_task_detail = {'hazard_solution': {'task_args': {'file_url': 'http://example.com/task_args.json'}}}

    mock_gtapi.get_oq_hazard_task.return_value = hazard_task_detail
    oq_config.download_artefacts(mock_gtapi, task_id, hazard_task_detail, subtasks_folder)

    assert (subtasks_folder / '12345' / 'task_args.json').exists()


def test_process_hdf5(mock_gtapi, tmp_path):
    subtasks_folder = tmp_path / 'subtasks'
    subtasks_folder.mkdir()
    task_id = '12345'
    hazard_task_detail = {
        'hazard_solution': {
            'id': '67890',
            'hdf5_archive': {'file_name': 'calc_1.hdf5.zip', 'file_url': 'http://example.com/calc_1.hdf5.zip'},
        }
    }

    mock_gtapi.get_oq_hazard_task.return_value = hazard_task_detail
    oq_config.process_hdf5(mock_gtapi, task_id, hazard_task_detail, subtasks_folder)

    assert (subtasks_folder / '12345' / 'calc_1.hdf5').exists()
    assert (subtasks_folder / '12345' / 'calc_1.hdf5.original').exists()


def test_config_from_task(tmp_path):
    subtasks_folder = tmp_path / 'subtasks'
    subtasks_folder.mkdir()
    task_id = '12345'
    ta = {
        'hazard_model-hazard_config': '{"key": "value"}',
        'site_params-vs30': 760,
        'intensity_spec': {'measures': ['PGA'], 'levels': [0.01, 0.02]},
    }

    task_args_file = subtasks_folder / str(task_id) / TASK_ARGS_JSON
    task_args_file.parent.mkdir()
    task_args_file.write_text(json.dumps(ta))

    config = oq_config.config_from_task(task_id, subtasks_folder)

    assert config.description == 'synthetic_job.ini'
    assert config.uniform_site_params['vs30'] == 760
    assert config.iml == {'PGA': [0.01, 0.02]}
