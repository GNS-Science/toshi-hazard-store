import pathlib
from unittest.mock import MagicMock

import pytest
from pytest_lazy_fixtures import lf

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)

# from toshi_hazard_store.model.hazard_models_pydantic import HazardCurveProducerConfig
from toshi_hazard_store.oq_import import oq_config, toshi_api_client

# Mocking the API client and other dependencies
TASK_ARGS_JSON = "task_args.json"


@pytest.fixture
def mock_chc_manager(tmpdir_factory):
    storage_folder = pathlib.Path(tmpdir_factory.mktemp("chc"))
    return CompatibleHazardCalculationManager(storage_folder)


@pytest.fixture
def mock_hpc_manager(mock_chc_manager, tmpdir_factory):
    storage_folder = pathlib.Path(tmpdir_factory.mktemp("hpc"))
    return HazardCurveProducerConfigManager(storage_folder, mock_chc_manager)


@pytest.fixture
def mock_gtapi():
    return MagicMock(
        toshi_api_client.ApiClient
    )  # CompatibleHazardCalculationManager(pathlib.Path('/mock/storage_folder'))


@pytest.fixture(
    params=[
        lf('old_skool_task_args'),
        lf('mid_skool_config'),
        lf('latest_config'),
    ]
)
def the_config(request):
    """Fixture to provide numbers for testing."""
    return request.param


# Test cases for oq_config functions
def test_download_artefacts(mock_gtapi, tmp_path, monkeypatch, the_config):
    subtasks_folder = tmp_path / 'subtasks'
    subtasks_folder.mkdir()
    task_id = '12345'

    # setup gtapi mock
    hazard_task_detail = {'hazard_solution': {'task_args': {'file_url': 'http://example.com/task_args.json'}}}
    mock_gtapi.get_oq_hazard_task.return_value = hazard_task_detail

    # setup requests mock
    mock_response = MagicMock()
    mock_response.content = open(the_config, 'rb').read()
    mock_response.ok = True
    monkeypatch.setattr(oq_config.requests, 'get', lambda *args, **kwargs: mock_response)

    oq_config.download_artefacts(mock_gtapi, task_id, hazard_task_detail, subtasks_folder)

    assert (subtasks_folder / '12345' / 'task_args.json').exists()
    assert open(subtasks_folder / '12345' / 'task_args.json', 'rb').read() == mock_response.content


# @pytest.mark.skip("WIP maybe not needed?")
@pytest.mark.parametrize("manipulate", [True, False])
def test_process_hdf5(mock_gtapi, solution_archive_fixture, tmp_path, monkeypatch, manipulate):
    subtasks_folder = tmp_path / 'subtasks'
    subtasks_folder.mkdir()
    task_id = '12345'
    (subtasks_folder / task_id).mkdir()

    hazard_task_detail = {
        'hazard_solution': {
            'id': '67890',
            'hdf5_archive': {'file_name': 'calc_1.hdf5.zip', 'file_url': 'http://example.com/calc_1.hdf5.zip'},
        }
    }

    mock_gtapi.get_oq_hazard_task.return_value = hazard_task_detail

    # path the api fetch, and
    monkeypatch.setattr(oq_config, '_save_api_file', lambda *args, **kwargs: solution_archive_fixture)

    assert solution_archive_fixture.exists()

    oq_config.process_hdf5(mock_gtapi, task_id, hazard_task_detail, subtasks_folder, manipulate=manipulate)

    assert not solution_archive_fixture.exists()
    assert (subtasks_folder / '12345' / 'calc_1.hdf5').exists()
    assert (subtasks_folder / '12345' / 'calc_1.hdf5.original').exists() == manipulate


def test_config_from_task_args_latest(tmp_path, latest_config, mock_task_args_file_path, task_id):
    subtasks_folder = mock_task_args_file_path.parent.parent
    config = oq_config.config_from_task(task_id, subtasks_folder)

    assert config.get_uniform_site_params()[0] == 760
    assert config.get_parameter("general", "description") == 'synthetic_job.ini'
    assert config.get_iml() == (['PGA', 'SA(0.5)', 'SA(1.5)', 'SA(3.0)'], [0.0001, 0.0002, 0.0004])
