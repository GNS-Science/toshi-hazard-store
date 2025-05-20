import json

from toshi_hazard_store.oq_import import oq_config

# import pytest


def test_parse_old_skool(old_skool_task_args, task_id):

    print(old_skool_task_args)
    config = oq_config.config_from_task(task_id, old_skool_task_args.parent.parent)
    print(config)

    assert config.get_parameter("erf", "rupture_mesh_spacing") == "4"
    assert config.get_parameter("general", "ps_grid_spacing") == "30"
    assert config.get_parameter("general", "description") == "synthetic_job.ini"
    assert config.get_parameter("site_params", "reference_vs30_value") == '275'

    imls = config.get_parameter("calculation", "intensity_measure_types_and_levels")

    imls = json.loads(imls.replace("], }", "] }"))
    assert imls.get("PGA")[:4] == [0.0001, 0.001, 1.0, 10.0]


def test_parse_mid_skool(mid_skool_config, task_id):
    ## WARNING this test is not validated against real world examples
    # there may be some differences in  GT yet to be preocessed.

    print(mid_skool_config)
    config = oq_config.config_from_task(task_id, mid_skool_config.parent.parent)
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
