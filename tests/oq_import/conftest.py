import json
import pathlib

import pytest

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


@pytest.fixture(scope='module')
def task_id():
    yield 'ABCD'


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
