import os
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds
import pytest
from nzshm_common import grids
from nzshm_common.location.coded_location import CodedLocation

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.model.pyarrow.dataset_schema import get_hazard_aggregate_schema


@pytest.fixture(scope='function')
def one_degree_hazard_sample_dataframe():
    """get a one-degree grid cell sample"""
    folder = Path(Path(os.path.realpath(__file__)).parent.parent, 'fixtures', 'aggregate_hazard')
    source_dir, source_filesystem = pyarrow_dataset.configure_output(str(folder))

    dataset = ds.dataset(
        source_dir,
        filesystem=source_filesystem,
        partitioning='hive',
        format='parquet',
        schema=get_hazard_aggregate_schema(),
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


@pytest.fixture(scope='function')
def get_one_degree_region_grid_fixture(one_degree_hazard_sample_dataframe):
    df = one_degree_hazard_sample_dataframe

    def get_coded_locations(df):
        for code in df.nloc_001.unique():
            tup = code.split('~')
            ftup = (float(tup[0]), float(tup[1]))
            yield CodedLocation.from_tuple(ftup)

    grid = list(get_coded_locations(df))
    yield grid
