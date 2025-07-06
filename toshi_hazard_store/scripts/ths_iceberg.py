'''
A script to explore the performance and use of AWS S3 tables / pyiceberg as a possible
alternative to AWS S3 General Purpose buckets.

See docs for results of initial tests. And there are also some real world tests in `nshm-hazard-graphql-api` project.

Brief summary of findings:

 - theres quite a bit of additional one-time setup to get AWS tables configured for pyiceberg.
 - with equivalaent partitioning there's very little difference in raw preformance pyiceberg vs pyarrow.
 - Testing here did not include optimising AWS tables.
 - AWS GLUE/ Iceberg do offer some  convenince factors perticualry around `shcema evolution`, however the
   need for this is not high in our use cases

 '''

import datetime as dt

import pyarrow.compute as pc
import pyarrow.dataset as ds
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import EqualTo, In

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.query import datasets
from toshi_hazard_store.query.hazard_query import downsample_code

DATASET_FORMAT = 'parquet'

# Constants
REGION = 'ap-southeast-2'
CATALOG = 's3tablescatalog'
DATABASE = 'ths_poc_iceberg_db'  # DATABASE -> Namepspace in pyiceberg terms
TABLE_BUCKET = 'pyiceberg-blog-bucket'
TABLE_BUCKET = 'ths-poc-iceberg'
TABLE_NAME = 'AGGR'

rest_args = {
    "type": "rest",
    "warehouse": f"461564345538:s3tablescatalog/{TABLE_BUCKET}",
    "uri": f"https://glue.{REGION}.amazonaws.com/iceberg",
    "rest.sigv4-enabled": "true",
    "rest.signing-name": "glue",
    "rest.signing-region": REGION,
}

imts = [
    "PGA",
    "SA(0.1)",
    "SA(0.2)",
    "SA(0.3)",
    "SA(0.4)",
    "SA(0.5)",
    "SA(0.7)",
    "SA(1.0)",
    "SA(1.5)",
    "SA(2.0)",
    "SA(3.0)",
    "SA(4.0)",
    "SA(5.0)",
    "SA(6.0)",
    "SA(7.5)",
    "SA(10.0)",
]
aggs = ["mean", "0.05", "0.95", "0.1", "0.9"]
loc = "-41.200~174.800"
vs30s = [400]


def import_to_iceberg():

    # warehouse_path = "WORKING/ICEBERG"
    # catalog_uri = "s3://ths-poc-arrow-test/ICEBERG_CATALOG"
    # catalog_uri = "s3://ths-poc-iceberg"

    # fltr = pc.field("nloc_001") == "-41.200~174.800"
    fltr = pc.field("vs30") == 400

    t0 = dt.datetime.now()
    aggr_uri = "s3://ths-dataset-prod/NZSHM22_AGG"
    source_dir, source_filesystem = pyarrow_dataset.configure_output(aggr_uri)
    dataset0 = ds.dataset(source_dir, filesystem=source_filesystem, format=DATASET_FORMAT, partitioning='hive')
    dt0 = dataset0.to_table(filter=fltr)

    t1 = dt.datetime.now()
    print(f"Opened pyarrow table in {(t1 - t0).total_seconds()}")

    rest_catalog = load_catalog(CATALOG, **rest_args)
    t1 = dt.datetime.now()
    print(rest_catalog)
    print(dir(rest_catalog))

    icetable = rest_catalog.create_table(identifier=f"{DATABASE}.{TABLE_NAME}", schema=dt0.schema)

    t2 = dt.datetime.now()
    print(f"created iceberg table in {(t2 - t1).total_seconds()}")

    icetable.append(dt0)
    rows = len(icetable.scan().to_arrow())
    # print(f"imported {rows} rows to table")

    t3 = dt.datetime.now()
    print(f"Saved {rows} rows to iceberg table in {(t3 - t2).total_seconds()}")

    print(icetable.scan(row_filter=EqualTo("vs30", 400) & EqualTo('aggr', 'mean')).to_pandas())


def query_arrow():

    fltr = (
        (pc.field('aggr').isin(aggs))
        & (pc.field("nloc_001").isin([loc]))
        & (pc.field("nloc_0").isin([downsample_code(loc, 1)]))
        & (pc.field("imt").isin(imts))
        & (pc.field("vs30").isin(vs30s))
    )
    # & (pc.field('hazard_model_id') == hazard_model)

    # print(fltr)
    t0 = dt.datetime.now()
    aggr_uri = "s3://ths-dataset-prod/NZSHM22_AGG"
    source_dir, source_filesystem = pyarrow_dataset.configure_output(aggr_uri)
    dataset0 = ds.dataset(source_dir, filesystem=source_filesystem, format=DATASET_FORMAT, partitioning='hive')

    t1 = dt.datetime.now()
    print(f"opened dateset in {(t1 - t0).total_seconds()}")

    dt0 = dataset0.to_table(filter=fltr)

    t2 = dt.datetime.now()
    print(f"opened table in {(t2 - t1).total_seconds()}")

    df0 = dt0.to_pandas()
    print(df0.shape)
    t3 = dt.datetime.now()

    print('>>>>>')
    print(f"Queried pyarrow table in {(t3 - t2).total_seconds()} secs")
    print(f"Total {(t3 - t0).total_seconds()} secs")
    print('>>>>>')


def query_ice():
    t0 = dt.datetime.now()
    rest_catalog = load_catalog(CATALOG, **rest_args)
    t1 = dt.datetime.now()
    print(f"opened catalog in {(t1 - t0).total_seconds()}")

    icetable = rest_catalog.load_table(
        identifier=f"{DATABASE}.{TABLE_NAME}",
    )
    t2 = dt.datetime.now()
    print(f"opened table in {(t2 - t1).total_seconds()}")

    filter = (
        In('aggr', aggs)
        & In('imt', imts)
        & In('aggr', aggs)
        & EqualTo("nloc_001", loc)
        & EqualTo("nloc_0", downsample_code(loc, 1))
        & EqualTo("vs30", 400)
    )

    res = icetable.scan(row_filter=filter, selected_fields=("nloc_001", "imt", "aggr", "values")).to_pandas()

    print(res.shape)
    t3 = dt.datetime.now()
    print('>>>>>')
    print(f"Queried iceberg table in {(t3 - t2).total_seconds()} secs")
    print(f"Total {(t3 - t0).total_seconds()} secs")
    print('>>>>>')


def query_datasets(query_fn):
    t0 = dt.datetime.now()
    MODEL = "NSHM_v1.0.4"
    res = list(query_fn(location_codes=[loc], vs30s=vs30s, hazard_model=MODEL, imts=imts, aggs=aggs))
    assert len(res) == 80
    print('>>>>>')
    t3 = dt.datetime.now()

    print(f"Total for Function {query_fn.__name__} {(t3 - t0).total_seconds()} secs")
    print('>>>>>')


if __name__ == "__main__":
    # import_to_iceberg()
    query_arrow()
    print()
    query_ice()
    print()
    for fn in [
        datasets.get_hazard_curves_naive,
        datasets.get_hazard_curves_by_vs30,
        datasets.get_hazard_curves_by_vs30_nloc0,
    ]:
        query_datasets(fn)
        print()
