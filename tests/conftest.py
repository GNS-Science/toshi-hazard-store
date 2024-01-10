import json
import os
from unittest import mock

import pytest
from moto import mock_dynamodb
from nzshm_common.location.code_location import CodedLocation

# from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model

from toshi_hazard_store import model
from toshi_hazard_store.v2.db_adapter import ensure_class_bases_begin_with

# from toshi_hazard_store.v2.db_adapter.sqlite import SqliteAdapter


@pytest.fixture()
def setenvvar(tmp_path):
    # ref https://adamj.eu/tech/2020/10/13/how-to-mock-environment-variables-with-pytest/
    envvars = {"THS_SQLITE_FOLDER": str(tmp_path), "THS_USE_SQLITE_ADAPTER": "TRUE"}
    with mock.patch.dict(os.environ, envvars, clear=True):
        yield  # This is the magical bit which restore the environment after


@pytest.fixture(scope="function")
def adapter_model():
    with mock_dynamodb():
        model.migrate()
        yield model
        model.drop_tables()


@pytest.fixture()
def get_one_meta():
    yield lambda: model.ToshiOpenquakeMeta(
        partition_key="ToshiOpenquakeMeta",
        hazard_solution_id="AMCDEF",
        general_task_id="GBBSGG",
        hazsol_vs30_rk="AMCDEF:350",
        # updated=dt.datetime.now(tzutc()),
        # known at configuration
        vs30=350,  # vs30 value
        imts=['PGA', 'SA(0.5)'],  # list of IMTs
        locations_id='AKL',  # Location code or list ID
        source_tags=["hiktlck", "b0.979", "C3.9", "s0.78"],
        source_ids=["SW52ZXJzaW9uU29sdXRpb25Ocm1sOjEwODA3NQ==", "RmlsZToxMDY1MjU="],
        inv_time=1.0,
        # extracted from the OQ HDF5
        src_lt=json.dumps(dict(sources=[1, 2])),  # sources meta as DataFrame JSON
        gsim_lt=json.dumps(dict(gsims=[1, 2])),  # gmpe meta as DataFrame JSON
        rlz_lt=json.dumps(dict(rlzs=[1, 2])),  # realization meta as DataFrame JSON
    )


@pytest.fixture(scope='function')
def get_one_rlz():
    imtvs = []
    for t in ['PGA', 'SA(0.5)', 'SA(1.0)']:
        levels = range(1, 51)
        values = range(101, 151)
        imtvs.append(model.IMTValuesAttribute(imt="PGA", lvls=levels, vals=values))

    location = CodedLocation(lat=-41.3, lon=174.78, resolution=0.001)
    yield lambda: model.OpenquakeRealization(
        values=imtvs,
        rlz=10,
        vs30=450,
        hazard_solution_id="AMCDEF",
        source_tags=["hiktlck", "b0.979", "C3.9", "s0.78"],
        source_ids=["SW52ZXJzaW9uU29sdXRpb25Ocm1sOjEwODA3NQ==", "RmlsZToxMDY1MjU="],
    ).set_location(location)


@pytest.fixture(autouse=True, scope="session")
def set_model():
    # set default model bases for pynamodb
    ensure_class_bases_begin_with(namespace=model.__dict__, class_name='ToshiOpenquakeMeta', base_class=Model)