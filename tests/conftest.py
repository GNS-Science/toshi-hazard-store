import logging
import os
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds
import pytest
from moto import mock_aws
from nzshm_common import grids
from nzshm_common.location.coded_location import CodedLocation
from nzshm_common.location.location import LOCATIONS_BY_ID

from toshi_hazard_store import model
from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve
from toshi_hazard_store.model.pyarrow import pyarrow_dataset

# Global AWS mock that must be set up BEFORE any imports that call AWS
_AWS_MOCK = None


def pytest_configure(config):
    """
    Configure pytest - runs before test collection.

    This sets up AWS mocking before any test modules are imported,
    preventing real AWS calls from dependencies like nzshm_model.
    """
    global _AWS_MOCK

    # Set environment variables before starting the mock
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    # Start the mock
    _AWS_MOCK = mock_aws()
    _AWS_MOCK.start()

    # Create the secrets that nzshm_model expects
    import boto3

    client = boto3.client("secretsmanager", region_name="us-east-1")
    client.create_secret(
        Name="NZSHM22_TOSHI_API_SECRET_PROD",
        SecretString='{"NZSHM22_TOSHI_API_KEY_PROD": "fake_api_key_for_testing"}',
    )
    client.create_secret(
        Name="NZSHM22_TOSHI_API_SECRET_TEST",
        SecretString='{"NZSHM22_TOSHI_API_KEY_TEST": "fake_api_key_for_testing"}',
    )


def pytest_unconfigure(config):
    """Clean up after all tests."""
    if _AWS_MOCK:
        _AWS_MOCK.stop()


log = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def many_rlz_args():
    yield dict(
        TOSHI_ID="FAk3T0sHi1D==",
        vs30s=[250, 500, 1000, 1500],
        imts=["PGA"],
        locs=[CodedLocation(o["latitude"], o["longitude"], 0.001) for o in list(LOCATIONS_BY_ID.values())[:2]],
        rlzs=[x for x in range(5)],
    )


@pytest.fixture(scope="session")
def many_hazagg_args():
    yield dict(
        HAZARD_MODEL_ID="MODEL_THE_FIRST",
        vs30s=[250, 350, 500, 1000, 1500],
        imts=["PGA", "SA(0.5)"],
        aggs=[model.AggregationEnum.MEAN.value, model.AggregationEnum._10.value],
        locs=[CodedLocation(o["latitude"], o["longitude"], 0.001) for o in list(LOCATIONS_BY_ID.values())],
    )


@pytest.fixture(scope="function")
def one_degree_hazard_sample_dataframe():
    """get a one-degree grid cell sample"""
    folder = Path(Path(os.path.realpath(__file__)).parent, "fixtures", "aggregate_hazard")
    source_dir, source_filesystem = pyarrow_dataset.configure_output(str(folder))

    dataset = ds.dataset(
        source_dir,
        filesystem=source_filesystem,
        partitioning="hive",
        format="parquet",
        schema=HazardAggregateCurve.pyarrow_schema(),
    )
    nloc0 = grids.get_location_grid("NZ_0_1_NB_1_1", 1.0)[0].code
    flt = (
        (pc.field("nloc_0") == nloc0)
        & (pc.field("vs30") == 400)
        & (pc.field("aggr").isin(["mean", "cov"]))
        & (pc.field("imt") == "PGA")
    )

    table = dataset.to_table(filter=flt)
    yield table.to_pandas()


@pytest.fixture(scope="function")
def get_one_degree_region_grid_fixture(one_degree_hazard_sample_dataframe):
    df = one_degree_hazard_sample_dataframe

    def get_coded_locations(df):
        for code in df.nloc_001.unique():
            tup = code.split("~")
            ftup = (float(tup[0]), float(tup[1]))
            yield CodedLocation.from_tuple(ftup)

    grid = list(get_coded_locations(df))
    yield grid
