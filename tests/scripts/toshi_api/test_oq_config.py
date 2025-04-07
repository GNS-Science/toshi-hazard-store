import json
import pathlib

import pytest

from toshi_hazard_store.oq_import import oq_config

mid_skool_config_example = {
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


@pytest.fixture
def mid_skool_config(tmpdir_factory):
    config_folder = pathlib.Path(tmpdir_factory.mktemp("mid_skool"))
    (config_folder / TASK_ID).mkdir()
    config_file = config_folder / TASK_ID / "task_args.json"
    with open(config_file, 'w') as config:
        config.write(json.dumps(mid_skool_config_example))
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

    imls = json.loads(imls.replace("], }", "] }"))
    assert imls.get("PGA")[:4] == [0.0001, 0.001, 1.0, 10.0]


def test_parse_mid_skool(mid_skool_config):
    ## WARNING this test is not validated against real world examples
    # there may be some differences in  GT yet to be preocessed.

    print(mid_skool_config)
    config = oq_config.config_from_task(TASK_ID, mid_skool_config.parent.parent)
    print(config)

    assert config.get_parameter("erf", "rupture_mesh_spacing") == "4"
    assert config.get_parameter("general", "ps_grid_spacing") == "30"
    assert config.get_parameter("general", "description") == "synthetic_job.ini"
    assert config.get_parameter("site_params", "reference_vs30_value") == '275'

    imls = config.get_parameter("calculation", "intensity_measure_types_and_levels")

    imls = json.loads(imls.replace("], }", "] }"))
    assert imls.get("PGA")[:4] == [0.0001, 0.001, 1.0, 10.0]


def test_parse_new_skool(latest_config):
    config = oq_config.config_from_task("T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz", latest_config.parent.parent)
    print(config)

    assert config.get_parameter("erf", "rupture_mesh_spacing") == "4"
    assert config.get_parameter("general", "ps_grid_spacing") == "30"
    # assert config.get_parameter("general", "description") == "synthetic_job.ini"
    assert config.get_parameter("site_params", "reference_vs30_value") == '275'

    imls = config.get_parameter("calculation", "intensity_measure_types_and_levels")
    imls = json.loads(imls.replace("], }", "] }"))
    assert imls.get("PGA")[:5] == [0.0001, 0.0002, 0.0004, 0.0006, 0.0008]
