# Testng iceberg and pyiceberg

using scripts/ths_iceberg.py

### Test 1 local catalog (sqlite)

#### one location 2 vs30

with:
```
aggr_uri = "s3://ths-dataset-prod/NZSHM22_AGG"
fltr = pc.field("nloc_001") == "-41.300~174.800"
```

```
chrisbc@MLX01 toshi-hazard-store % time poetry run python toshi_hazard_store/scripts/ths_iceberg.py
Opened pyarrow table in 10.826197
created iceberg table in 0.104256
Saved 1080 rows to iceberg table in 0.057077
poetry run python toshi_hazard_store/scripts/ths_iceberg.py  3.43s user 3.68s system 59% cpu 12.010 total
```

#### all locations, 1 vs30

with: 
```
# fltr = pc.field("nloc_001") == "-41.200~174.800"
fltr = pc.field("vs30") == 400
```

```
chrisbc@MLX01 toshi-hazard-store % time poetry run python toshi_hazard_store/scripts/ths_iceberg.py
Opened pyarrow table in 21.961363
created iceberg table in 0.123352
Saved 2020140 rows to iceberg table in 15.482653
poetry run python toshi_hazard_store/scripts/ths_iceberg.py  51.75s user 13.20s system 165% cpu 39.259 total
```

### Test 2 S3 GP catalog (in-memory)

#### one location 2 vs30

with:
```
aggr_uri = "s3://ths-dataset-prod/NZSHM22_AGG"
fltr = pc.field("nloc_001") == "-41.300~174.800"
catalog_uri = "s3://ths-poc-arrow-test/ICEBERG_CATALOG"
```

```
time poetry run python toshi_hazard_store/scripts/ths_iceberg.py
Opened pyarrow table in 12.224047
created iceberg table in 2.071799
Saved 1080 rows to iceberg table in 3.24654
poetry run python toshi_hazard_store/scripts/ths_iceberg.py  3.54s user 3.81s system 38% cpu 18.862 total
```

### Test 2 S3 Table catalog (in-memory)

#### one location 2 vs30

with:
```
aggr_uri = "s3://ths-dataset-prod/NZSHM22_AGG"
fltr = pc.field("nloc_001") == "-41.300~174.800"
catalog_uri = "s3://ths-poc-iceberg"
```

```
poetry run python toshi_hazard_store/scripts/ths_iceberg.py  3.54s user 3.81s system 38% cpu 18.862 total
chrisbc@MLX01 toshi-hazard-store % time poetry run python toshi_hazard_store/scripts/ths_iceberg.py
Opened pyarrow table in 11.932467
Unable to resolve region for bucket ths-poc-iceberg
Traceback (most recent call last):
  File "/Users/Shared/DEV/GNS/LIB/toshi-hazard-store/toshi_hazard_store/scripts/ths_iceberg.py", line 55, in <module>
    import_to_iceberg()
  File "/Users/Shared/DEV/GNS/LIB/toshi-hazard-store/toshi_hazard_store/scripts/ths_iceberg.py", line 41, in import_to_iceberg
    icetable = catalog.create_table("DEFAULT.aggr", schema=dt0.schema)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/chrisbc/Library/Caches/pypoetry/virtualenvs/toshi-hazard-store--2imPOIE-py3.12/lib/python3.12/site-packages/pyiceberg/catalog/sql.py", line 217, in create_table
    self._write_metadata(metadata, io, metadata_location)
  File "/Users/chrisbc/Library/Caches/pypoetry/virtualenvs/toshi-hazard-store--2imPOIE-py3.12/lib/python3.12/site-packages/pyiceberg/catalog/__init__.py", line 939, in _write_metadata
    ToOutputFile.table_metadata(metadata, io.new_output(metadata_path))
  File "/Users/chrisbc/Library/Caches/pypoetry/virtualenvs/toshi-hazard-store--2imPOIE-py3.12/lib/python3.12/site-packages/pyiceberg/serializers.py", line 130, in table_metadata
    with output_file.create(overwrite=overwrite) as output_stream:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/chrisbc/Library/Caches/pypoetry/virtualenvs/toshi-hazard-store--2imPOIE-py3.12/lib/python3.12/site-packages/pyiceberg/io/pyarrow.py", line 341, in create
    output_file = self._filesystem.open_output_stream(self._path, buffer_size=self._buffer_size)
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "pyarrow/_fs.pyx", line 885, in pyarrow._fs.FileSystem.open_output_stream
  File "pyarrow/error.pxi", line 155, in pyarrow.lib.pyarrow_internal_check_status
  File "pyarrow/error.pxi", line 92, in pyarrow.lib.check_status
OSError: When initiating multiple part upload for key 'DEFAULT.db/aggr/metadata/00000-414345b9-2ea8-46fe-ace5-636a7ddadf41.metadata.json' in bucket 'ths-poc-iceberg': AWS Error NO_SUCH_BUCKET during CreateMultipartUpload operation: The specified bucket does not exist
poetry run python toshi_hazard_store/scripts/ths_iceberg.py  3.49s user 3.73s system 45% cpu 15.735 total
```

THIS WONT WORK

### Test 3 using AWS Glue 

followign https://aws.amazon.com/blogs/storage/access-data-in-amazon-s3-tables-using-pyiceberg-through-the-aws-glue-iceberg-rest-endpoint/

with :

```
REGION = 'ap-southeast-2'
CATALOG = 's3tablescatalog'
DATABASE = 'ths_poc_iceberg_db'  # DATABASE -> Namepspace in pyiceberg terms
TABLE_BUCKET = 'ths-poc-iceberg'
TABLE_NAME = 'AGGR'
```

```
time poetry run python toshi_hazard_store/scripts/ths_iceberg.py
Opened pyarrow table in 24.090168
s3tablescatalog (<class 'pyiceberg.catalog.rest.RestCatalog'>)
['__abstractmethods__', '__annotations__', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__weakref__', '_abc_impl', '_check_valid_namespace_identifier', '_config_headers', '_convert_schema_if_needed', '_create_session', '_create_table', '_delete_old_metadata', '_extract_optional_oauth_params', '_fetch_access_token', '_fetch_config', '_handle_non_200_response', '_identifier_to_validated_tuple', '_init_sigv4', '_load_file_io', '_refresh_token', '_remove_catalog_name_from_table_request_identifier', '_response_to_staged_table', '_response_to_table', '_session', '_split_identifier_for_json', '_split_identifier_for_path', '_warn_oauth_tokens_deprecation', 'auth_url', 'commit_table', 'create_namespace', 'create_namespace_if_not_exists', 'create_table', 'create_table_if_not_exists', 'create_table_transaction', 'drop_namespace', 'drop_table', 'drop_view', 'identifier_to_database', 'identifier_to_database_and_table', 'identifier_to_tuple', 'list_namespaces', 'list_tables', 'list_views', 'load_namespace_properties', 'load_table', 'name', 'namespace_exists', 'namespace_from', 'namespace_to_string', 'properties', 'purge_table', 'register_table', 'rename_table', 'table_exists', 'table_name_from', 'update_namespace_properties', 'uri', 'url', 'view_exists']
created iceberg table in 1.939119
Saved 2020140 rows to iceberg table in 42.426441
       compatible_calc_id hazard_model_id  aggr                                             values      imt         nloc_001  vs30       nloc_0
0                 NZSHM22     NSHM_v1.0.4  mean  [0.051696815, 0.05169638, 0.051679485, 0.05160...      PGA  -34.300~172.900   400  -34.0~173.0
1                 NZSHM22     NSHM_v1.0.4  mean  [0.052680086, 0.052679673, 0.052663658, 0.0525...      PGA  -34.300~173.000   400  -34.0~173.0
2                 NZSHM22     NSHM_v1.0.4  mean  [0.05444223, 0.054441817, 0.05442487, 0.054347...      PGA  -34.300~173.100   400  -34.0~173.0
3                 NZSHM22     NSHM_v1.0.4  mean  [0.048430245, 0.04842985, 0.04841446, 0.048345...      PGA  -34.400~172.600   400  -34.0~173.0
4                 NZSHM22     NSHM_v1.0.4  mean  [0.05057133, 0.050570954, 0.050555933, 0.05048...      PGA  -34.400~172.700   400  -34.0~173.0
...                   ...             ...   ...                                                ...      ...              ...   ...          ...
101002            NZSHM22     NSHM_v1.0.4  mean  [0.17536972, 0.13379893, 0.098121226, 0.079893...  SA(7.5)  -46.600~169.500   400  -47.0~170.0
101003            NZSHM22     NSHM_v1.0.4  mean  [0.1706562, 0.1300151, 0.0952137, 0.07742944, ...  SA(7.5)  -46.600~169.600   400  -47.0~170.0
101004            NZSHM22     NSHM_v1.0.4  mean  [0.16497253, 0.12532957, 0.091469646, 0.074174...  SA(7.5)  -46.600~169.700   400  -47.0~170.0
101005            NZSHM22     NSHM_v1.0.4  mean  [0.15930109, 0.120670915, 0.0876214, 0.0707053...  SA(7.5)  -46.600~169.800   400  -47.0~170.0
101006            NZSHM22     NSHM_v1.0.4  mean  [0.16793892, 0.12838548, 0.09438368, 0.0769320...  SA(7.5)  -46.700~169.500   400  -47.0~170.0

[101007 rows x 8 columns]
poetry run python toshi_hazard_store/scripts/ths_iceberg.py  56.79s user 16.48s system 86% cpu 1:24.27 total
```

### Test 4 query performance comparision

Here's aa a simple test retrieving the typical 80 user curves for NSHM Korroaa....

```
chrisbc@MLX01 toshi-hazard-store % time poetry run python toshi_hazard_store/scripts/ths_iceberg.py
opened dateset in 0.573172
opened table in 0.538331
(80, 8)
>>>>>
Queried pyarrow table in 0.002323 secs
Total 1.113826 secs
>>>>>

opened catalog in 0.390378
opened table in 1.20442
(80, 4)
>>>>>
Queried iceberg table in 15.744698 secs
Total 17.339496 secs
>>>>>
poetry run python toshi_hazard_store/scripts/ths_iceberg.py  2.03s user 3.88s system 30% cpu 19.316 total
```

The pyarrow version is now way faster, because it's using partitioning. note that the slower setup (opening dataset/table) will be cached.