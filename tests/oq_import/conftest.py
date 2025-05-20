import json
import pathlib

import pytest

TASK_ID = "TID12345"
GT_ID = "GTXYZ=="
TASK_ARGS_JSON = "task_args.json"


@pytest.fixture
def task_id():
    yield TASK_ID


@pytest.fixture
def general_task_id():
    yield GT_ID


mid_skool_task_args_example = {
    'vs30': 275,
    'oq': {
        'general': {'random_seed': 25, 'calculation_mode': 'classical', 'ps_grid_spacing': 30},
        'logic_tree': {'number_of_logic_tree_samples': 0},
        'erf': {
            'rupture_mesh_spacing': 4,
            'width_of_mfd_bin': 0.1,
            'complex_fault_mesh_spacing': 10.0,
            'area_source_discretization': 10.0,
        },
        'site_params': {'reference_vs30_type': 'measured'},
        'calculation': {
            'investigation_time': 1.0,
            'truncation_level': 4,
            'maximum_distance': {'Active Shallow Crust': '[[4.0, 0], [5.0, 100.0], [6.0, 200.0], [9.5, 300.0]]'},
        },
        'output': {'individual_curves': 'true'},
    },
    'intensity_spec': {
        'tag': 'fixed',
        'measures': [
            'PGA',
            'SA(0.1)',
            'SA(4.5)',
        ],
        'levels': [
            0.0001,
            0.001,
            1.0,
            10.0,
        ],
    },
}

old_skool_task_args_example = {
    'config_archive_id': 'RmlsZToxMjkxNjk4',
    'model_type': 'COMPOSITE',
    'logic_tree_permutations': [
        {
            'tag': 'GRANULAR',
            'weight': 1.0,
            'permute': [
                {
                    'group': 'ALL',
                    'members': [
                        {
                            'tag': 'geodetic, TI, N2.7, b0.823 C4.2 s1.41',
                            'inv_id': 'SW52ZXJzaW9uU29sdXRpb25Ocm1sOjEyOTE1MDI=',
                            'bg_id': 'RmlsZToxMzA3MTM=',
                            'weight': 1.0,
                        }
                    ],
                }
            ],
        }
    ],
    'intensity_spec': {
        'tag': 'fixed',
        'measures': [
            'PGA',
            'SA(0.1)',
            'SA(4.5)',
        ],
        'levels': [
            0.0001,
            0.001,
            1.0,
            10.0,
        ],
    },
    'vs30': 275,
    'location_list': ['NZ', 'NZ_0_1_NB_1_1', 'SRWG214'],
    'disagg_conf': {'enabled': False, 'config': {}},
    'rupture_mesh_spacing': 4,
    'ps_grid_spacing': 30,
    'split_source_branches': False,
}


@pytest.fixture
def old_skool_task_args(tmpdir_factory, task_id):
    config_folder = pathlib.Path(tmpdir_factory.mktemp("old_skool"))
    (config_folder / task_id).mkdir()
    config_file = config_folder / task_id / "task_args.json"
    with open(config_file, 'w') as config:
        config.write(json.dumps(old_skool_task_args_example))
    config.close()
    yield config_file


@pytest.fixture
def mid_skool_config(tmpdir_factory, task_id):
    config_folder = pathlib.Path(tmpdir_factory.mktemp("mid_skool"))
    (config_folder / task_id).mkdir()
    config_file = config_folder / task_id / "task_args.json"
    with open(config_file, 'w') as config:
        config.write(json.dumps(mid_skool_task_args_example))
    config.close()
    yield config_file


@pytest.fixture
def latest_config():
    fname = "R2VuZXJhbFRhc2s6NjkzMTg5Mg==/subtasks/T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/task_args.json"
    yield pathlib.Path(__file__).parent / "fixtures" / fname


@pytest.fixture
def solution_archive_fixture(tmpdir_factory):
    storage_folder = pathlib.Path(tmpdir_factory.mktemp("solution_archive_fixture"))
    fixture = (
        pathlib.Path(__file__).parent / 'fixtures' / 'openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazoxMDYzMzU3.zip'
    )

    # copy fixture data
    tmp_file = storage_folder / fixture.name
    tmp_file.write_bytes(fixture.read_bytes())
    return tmp_file


@pytest.fixture(scope="session")
def hdf5_calc_fixture():
    hdf5_fixture = (
        pathlib.Path(__file__).parent.parent
        / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
    )
    yield hdf5_fixture


@pytest.fixture
def mock_task_args_file_path(tmp_path, latest_config):

    # mock artefects
    subtasks_folder = tmp_path / GT_ID / 'subtasks'
    subtasks_folder.mkdir(parents=True)
    # task_id = '12345'
    ta_fixt = json.load(open(latest_config, 'r'))
    ta = {
        "hazard_model-hazard_config": ta_fixt.get("hazard_model-hazard_config"),
        'site_params-vs30': 760,
        'intensity_spec': {'measures': ['PGA'], 'levels': [0.01, 0.02]},
        "hazard_curve-imts": ["PGA", "SA(0.5)", "SA(1.5)", "SA(3.0)"],
        "hazard_curve-imtls": [
            0.0001,
            0.0002,
            0.0004,
        ],
        "site_params-locations": ["WLG", "AKL", "DUD", "CHC"],
        "site_params-locations_file": None,
    }

    task_args_file = subtasks_folder / str(TASK_ID) / TASK_ARGS_JSON
    task_args_file.parent.mkdir()
    task_args_file.write_text(json.dumps(ta))
    # config = oq_config.config_from_task(task_id, subtasks_folder)
    yield task_args_file
