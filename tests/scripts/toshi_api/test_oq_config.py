import json
import pathlib

import pytest

from toshi_hazard_store.scripts.revision_4 import oq_config

newer_skool_config_example = {
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
}

old_skool_config_example = {
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
            'SA(0.2)',
            'SA(0.3)',
            'SA(0.4)',
            'SA(0.5)',
            'SA(0.7)',
            'SA(1.0)',
            'SA(1.5)',
            'SA(2.0)',
            'SA(3.0)',
            'SA(4.0)',
            'SA(5.0)',
            'SA(6.0)',
            'SA(7.5)',
            'SA(10.0)',
            'SA(0.15)',
            'SA(0.25)',
            'SA(0.35)',
            'SA(0.6)',
            'SA(0.8)',
            'SA(0.9)',
            'SA(1.25)',
            'SA(1.75)',
            'SA(2.5)',
            'SA(3.5)',
            'SA(4.5)',
        ],
        'levels': [
            0.0001,
            0.0002,
            0.0004,
            0.0006,
            0.0008,
            0.001,
            0.002,
            0.004,
            0.006,
            0.008,
            0.01,
            0.02,
            0.04,
            0.06,
            0.08,
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.2,
            1.4,
            1.6,
            1.8,
            2.0,
            2.2,
            2.4,
            2.6,
            2.8,
            3.0,
            3.5,
            4,
            4.5,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0,
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

TASK_ID = 'ABCD'


@pytest.fixture
def old_skool_config(tmpdir_factory):
    config_folder = pathlib.Path(tmpdir_factory.mktemp("old_skool"))
    (config_folder / TASK_ID).mkdir()
    config_file = config_folder / TASK_ID / "task_args.json"
    with open(config_file, 'w') as config:
        config.write(json.dumps(old_skool_config_example))
    config.close()
    yield config_file


def newer_skool_config(tmpdir_factory):
    config_folder = pathlib.Path(tmpdir_factory.mktemp("old_skool"))
    (config_folder / TASK_ID).mkdir()
    config_file = config_folder / TASK_ID / "task_args.json"
    with open(config_file, 'w') as config:
        config.write(json.dumps(newer_skool_config_example))
    config.close()
    yield config_file


@pytest.fixture
def latest_config():
    fname = "R2VuZXJhbFRhc2s6NjkzMTg5Mg==/subtasks/T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/task_args.json"
    yield pathlib.Path(__file__).parent.parent / "fixtures" / fname


def test_parse_old_skool(old_skool_config):

    print(old_skool_config)
    config = oq_config.config_from_task(TASK_ID, old_skool_config.parent.parent)
    print(config)

    assert config.get_parameter("erf", "rupture_mesh_spacing") == "4"
    assert config.get_parameter("general", "ps_grid_spacing") == "30"
    assert config.get_parameter("general", "description") == "synthetic_job.ini"
    assert config.get_parameter("site_params", "reference_vs30_value") == '275'

    imls = config.get_parameter("calculation", "intensity_measure_types_and_levels")
    # print(imls)
    # print()
    # print(imls.replace("], }", "] }"))

    imls = json.loads(imls.replace("], }", "] }"))
    assert imls.get("PGA")[:5] == [0.0001, 0.0002, 0.0004, 0.0006, 0.00080]


@pytest.mark.skip('wip')
def test_latest_config_skool(latest_config):
    config = oq_config.config_from_task("T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz", latest_config.parent.parent)
    print(config)
    assert 0
