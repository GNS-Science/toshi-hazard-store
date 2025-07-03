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