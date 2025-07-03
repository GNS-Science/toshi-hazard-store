import datetime as dt

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

from pyiceberg.catalog import load_catalog
from toshi_hazard_store.model.pyarrow import pyarrow_dataset

DATASET_FORMAT = 'parquet'

def import_to_iceberg():

    warehouse_path = "WORKING/ICEBERG"
    aggr_uri = "s3://ths-dataset-prod/NZSHM22_AGG"

    # fltr = pc.field("nloc_001") == "-41.200~174.800"
    fltr = pc.field("vs30") == 400
    
    t0 = dt.datetime.now()
    source_dir, source_filesystem = pyarrow_dataset.configure_output(aggr_uri)
    dataset0 = ds.dataset(source_dir, filesystem=source_filesystem, format=DATASET_FORMAT, partitioning='hive')
    dt0 = dataset0.to_table(filter=fltr)

    t1 = dt.datetime.now()
    print(f"Opened pyarrow table in {(t1-t0).total_seconds()}")

    catalog = load_catalog(
        "default",
        **{
            'type': 'sql',
            "uri": f"sqlite:///{warehouse_path}/pyiceberg_catalog.db",
            "warehouse": f"file://{warehouse_path}",
        },
    )

    catalog.create_namespace("vs30_400")
    icetable = catalog.create_table("vs30_400.aggr", schema=dt0.schema)
    
    t2 = dt.datetime.now()
    print(f"created iceberg table in {(t2-t1).total_seconds()}")

    icetable.append(dt0)
    rows = len(icetable.scan().to_arrow())
    # print(f"imported {rows} rows to table")

    t3 = dt.datetime.now()
    print(f"Saved {rows} rows to iceberg table in {(t3-t2).total_seconds()}")


if __name__ == "__main__":
    import_to_iceberg()