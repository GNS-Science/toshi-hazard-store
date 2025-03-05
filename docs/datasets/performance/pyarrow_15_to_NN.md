## baseline performance tests

We started using pyarrow with version 14/15 and now it's up to at least 19.0.1

### FILTER 
#### Version 15.0.2
use `scripts\ths_r4_filter_dataset.py` to produce a filtered dataset from larger one.

```
time poetry run python scripts/ths_r4_filter_dataset.py WORKING/ARROW/THS_R4_HIVE WORKING/ARROW/TMP --verbose
using pyarrow version 15.0.2
((nloc_0 == "-37.0~175.0") and (nloc_001 == "-36.852~174.763"))
...
((nloc_0 == "-46.0~171.0") and (nloc_001 == "-45.874~170.504"))

filter 12 locations to WORKING/ARROW

real    2m34.869s
user    20m43.290s
sys     1m11.017s
```

#### Version 19.0.1

```
time poetry run python scripts/ths_r4_filter_dataset.py WORKING/ARROW/THS_R4_HIVE WORKING/ARROW/TMP --verbose
using pyarrow version 19.0.1
((nloc_0 == "-37.0~175.0") and (nloc_001 == "-36.852~174.763"))
...
((nloc_0 == "-46.0~171.0") and (nloc_001 == "-45.874~170.504"))
filter 12 locations to WORKING/ARROW/TMP

real    2m29.080s
user    19m51.944s
sys     1m11.387s
```

## Defrag /reorg 

Use `scripts\ths_r4_defrag.py` to compact / restructure partioning. This is single threaded.

### Reorg small

V1: Approx: 4m30

#### Run 1

##### Version 15
```
chrisbc@tryharder-ubuntu:/GNSDATA/LIB/toshi-hazard-store$ time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG --verbose
using pyarrow version 15.0.2
partitions: []
partition WORKING/ARROW/TMP/nloc_0=-41.0~175.0
...
compacted WORKING/ARROW/TMP/nloc_0=-37.0~175.0
compacted 12 partitions for WORKING/ARROW

real    4m38.415s
user    15m11.949s
sys     11m2.965s
```
##### Version 19.0.1

```
time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG --verbose
using pyarrow version 19.0.1
partitions: []
compacted WORKING/ARROW/TMP/nloc_0=-41.0~175.0 has disk size: 494MB
...
pyarrow RSS memory: 466MB
compacted 12 partitions for WORKING/ARROW

real    4m9.106s
user    14m18.134s
sys     10m32.759s
```

#### Run 2

```
chrisbc@tryharder-ubuntu:/GNSDATA/LIB/toshi-hazard-store$ time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG --verbose
using pyarrow version 15.0.2
partitions: []
compacted WORKING/ARROW/TMP/nloc_0=-41.0~175.0
RSS: 494MB
...
compacted 12 partitions for WORKING/ARROW

real    4m32.951s
user    15m4.936s
sys     11m4.036s
```

#### Run 3

```
chrisbc@tryharder-ubuntu:/GNSDATA/LIB/toshi-hazard-store$ time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG -p vs30 --verbose
using pyarrow version 15.0.2
partitions: ['vs30']
compacted WORKING/ARROW/TMP/nloc_0=-41.0~175.0;
...
compacted 12 partitions for WORKING/ARROW

real    4m17.809s
user    15m27.989s
sys     10m44.570s
```

#### Run 4

```
chrisbc@tryharder-ubuntu:/GNSDATA/LIB/toshi-hazard-store$ time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG -p vs30 --verbose
using pyarrow version 15.0.2
partitions: ['vs30']
compacted WORKING/ARROW/TMP/nloc_0=-41.0~175.0 has disk size: 523MB
...
pyarrow RSS memory: 494MB
compacted 12 partitions for WORKING/ARROW

real    4m20.796s
user    15m36.431s
sys     10m48.709s
```


#### Run 5

##### Version 15.0.2
```
chrisbc@tryharder-ubuntu:/GNSDATA/LIB/toshi-hazard-store$ time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG -p 'vs30, imt' --verbose
using pyarrow version 15.0.2
partitions: ['vs30', 'imt']
pyarrow RSS memory: 494MB
compacted 12 partitions for WORKING/ARROW

real    0m55.419s
user    8m40.011s
sys     0m39.568s
```

##### Version 19.0.1
```
time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG -p 'vs30, imt' --verbose
using pyarrow version 19.0.1
partitions: ['vs30', 'imt']
compacted WORKING/ARROW/TMP/nloc_0=-41.0~175.0 has disk size: 494MB
...
compacted WORKING/ARROW/TMP/nloc_0=-37.0~175.0 has disk size: 494MB
pyarrow RSS memory: 466MB
compacted 12 partitions for WORKING/ARROW

real    0m48.516s
user    8m8.439s
sys     0m27.097s
```

#### Reorg larger

NOTE this is the F32 dataset which is much more compact and therefore faster, despite having many more values.

##### Version 15.0.2
```
$ time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/THS_R4_F32 WORKING/ARROW/TMP_DEFRAG -p 'vs30, imt' --verbose
using pyarrow version 15.0.2
partitions: ['vs30', 'imt']
compacted WORKING/ARROW/THS_R4_F32/nloc_0=-41.0~175.0 has disk size: 500MB
...
pyarrow RSS memory: 27MB
compacted 64 partitions for WORKING/ARROW

real    6m17.818s
user    48m52.176s
sys     3m5.129s
```

##### Version 19.0.1

```
time poetry run python scripts/ths_r4_defrag.py WORKING/ARROW/TMP WORKING/ARROW/TMP_DEFRAG --verbose
using pyarrow version 19.0.1
partitions: []
compacted WORKING/ARROW/TMP/nloc_0=-41.0~175.0 has disk size: 494MB
....
pyarrow RSS memory: 46MB
compacted 64 partitions for WORKING/ARROW

real    5m49.718s
user    45m26.746s
sys     2m35.294s
```