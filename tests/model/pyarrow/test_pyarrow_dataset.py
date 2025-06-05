import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pytest

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.model.pyarrow.dataset_schema import get_hazard_realisation_schema


@pytest.fixture
def random_hazard_rlz_curves():
    def some_curves(n=10):
        for i in range(n):
            yield dict(
                compatible_calc_id="NZSHM22",
                producer_digest="digest for the producer look up",
                config_digest="digest for the job configuration",
                calculation_id="original calculation",
                rlz="rlz-000",  # the rlz id from the the original calculation
                sources_digest="# a unique hash",  # id for the NSHM LTB source branch
                gmms_digest="a unique hash id",  # for the NSHM LTB gsim branch
                nloc_001="-100.100~45.045",
                nloc_0="-100.0~45.0",
                imt="PGA",
                vs30=1000,
                values=[(x / 1000) for x in range(44)],
            )

    yield some_curves()


def test_configure_output_s3():
    ds = "s3://a_place_in_the_sun/root/"
    base_dir, filesystem = pyarrow_dataset.configure_output(ds)
    assert isinstance(filesystem, pa.fs.S3FileSystem)
    assert base_dir == 'a_place_in_the_sun/root'


def test_configure_output_local():
    ds = "\a_place_in_the_sun\root"
    base_dir, filesystem = pyarrow_dataset.configure_output(ds)
    assert isinstance(filesystem, pa.fs.LocalFileSystem)
    assert ds in base_dir


def test_serialise_realisation_curves_raises(tmp_path, random_hazard_rlz_curves):
    output_folder = tmp_path / "ds_direct"

    partitioning = ['vs30', 'nloc_0']
    base_dir, filesystem = pyarrow_dataset.configure_output(str(output_folder))

    with pytest.raises(TypeError, match=r"must be a pyarrow Table or RecordBatchReader"):
        pyarrow_dataset.append_models_to_dataset(
            random_hazard_rlz_curves, base_dir=base_dir, filesystem=filesystem, partitioning=partitioning
        )


def test_serialise_realisation_curves(tmp_path, random_hazard_rlz_curves):
    output_folder = tmp_path / "ds_direct"

    partitioning = ['vs30', 'nloc_0']
    base_dir, filesystem = pyarrow_dataset.configure_output(str(output_folder))

    item_dicts = [rlz for rlz in random_hazard_rlz_curves]
    df = pd.DataFrame(item_dicts)
    table = pa.Table.from_pandas(df)

    pyarrow_dataset.append_models_to_dataset(table, base_dir=base_dir, filesystem=filesystem, partitioning=partitioning)

    # read and check the dataset
    dataset = ds.dataset(output_folder, format='parquet', partitioning='hive', schema=get_hazard_realisation_schema())
    table = dataset.to_table()
    dfout = table.to_pandas()

    print(dfout.shape)
    print(dfout.tail())
    print(dfout.info())
    assert dfout.shape == (10, 12)
