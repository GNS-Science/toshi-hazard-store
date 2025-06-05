import pyarrow.dataset as ds
import pytest

from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve
from toshi_hazard_store.model.pyarrow import pyarrow_aggr_dataset, pyarrow_dataset
from toshi_hazard_store.model.pyarrow.dataset_schema import get_hazard_aggregate_schema


@pytest.fixture
def random_hazard_curves():
    def some_curves(n=10):
        for i in range(n):
            yield HazardAggregateCurve(
                compatible_calc_id="NZSHM22",
                hazard_model_id="MyNewModel",
                nloc_001="-100.100~45.045",
                nloc_0="-100.0~45.0",
                imt="PGA",
                vs30="1000",
                aggr="mean",
                values=[(x / 1000) for x in range(44)],
            )

    yield some_curves()


def test_serialise_aggregate_hazard_curves(tmp_path, random_hazard_curves):

    output_folder = tmp_path / "ds_direct"

    partitioning = ['vs30', 'nloc_0']
    base_dir, filesystem = pyarrow_dataset.configure_output(str(output_folder))
    pyarrow_aggr_dataset.append_models_to_dataset(
        models=random_hazard_curves, base_dir=base_dir, filesystem=filesystem, partitioning=partitioning
    )

    # read and check the dataset
    schema = get_hazard_aggregate_schema()
    dataset = ds.dataset(output_folder, format='parquet', partitioning='hive', schema=schema)
    table = dataset.to_table()
    dfout = table.to_pandas()

    print("out df >>>")
    print(dfout.shape)
    print(dfout.tail())
    print(dfout.info())
    print("out df <<<")
    assert dfout.shape == (10, 8)
