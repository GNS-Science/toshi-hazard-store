"""
Basic model migration, structure
"""

import pyarrow as pa
import pyarrow.dataset as ds
import pytest
from pyarrow import fs

from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve
from toshi_hazard_store.model.pyarrow import pyarrow_aggr_dataset, pyarrow_dataset


# Test pyarrow HazardAggregation models
def test_HazardAggregation_roundtrip_dataset(pyarrow_aggregation_models, tmp_path):

    output_folder = tmp_path / "ds"

    models = pyarrow_aggregation_models()

    print(models)
    filesystem = fs.LocalFileSystem()

    # write the dataset
    pyarrow_aggr_dataset.append_models_to_dataset(models, output_folder, filesystem=filesystem)

    # read and check the dataset
    dataset = ds.dataset(output_folder, filesystem=filesystem, format='parquet', partitioning='hive')
    table = dataset.to_table()
    df = table.to_pandas()

    expected = pyarrow_dataset.table_from_models(pyarrow_aggregation_models())

    assert table.shape == expected.shape
    assert df.shape == expected.shape


def test_HazardAggregation_write_dataset_with_bad_schema(pyarrow_aggregation_models, tmp_path, monkeypatch):

    # monkeypatch with a bad schema
    bad_schema = pa.schema([("mumbo", pa.string()), ("jumbo", pa.string())])
    monkeypatch.setattr(HazardAggregateCurve, "pyarrow_schema", lambda x: bad_schema)

    with pytest.raises(
        # pa.lib.ArrowTypeError, match=r"which does not match expected schema\n.*mumbo"
        KeyError,
        match=r"name 'mumbo' present in the specified schema is not found in the columns or index",
    ):
        output_folder = tmp_path / "ds"
        models = pyarrow_aggregation_models()
        filesystem = fs.LocalFileSystem()
        pyarrow_aggr_dataset.append_models_to_dataset(models, output_folder, filesystem=filesystem)


def test_HazardAggregation_read_dataset_with_bad_schema_doesnt_raise(pyarrow_aggregation_models, tmp_path, monkeypatch):

    dataset_folder = tmp_path / "ds"
    models = pyarrow_aggregation_models()
    filesystem = fs.LocalFileSystem()

    pyarrow_aggr_dataset.append_models_to_dataset(models, dataset_folder, filesystem=filesystem)

    # I expected this should raise exception about the schema mismatch
    # based on https://arrow.apache.org/docs/python/generated/pyarrow.\
    #  dataset.Dataset.html#pyarrow.dataset.Dataset.replace_schema

    # however, pyarrow won't verify the schema matches
    bad_schema = pa.schema([("numeric", pa.int64()), ("mumbo", pa.string()), ("jumbo", pa.string())])
    dataset = ds.dataset(
        dataset_folder, schema=bad_schema, format='parquet', filesystem=filesystem, partitioning='hive'
    )
    table = dataset.to_table()
    df = table.to_pandas()

    print(df)  # still no exception

    # but we can do it ourselves
    with pytest.raises(AssertionError):
        assert dataset.schema == HazardAggregateCurve.pyarrow_schema()
