# Summary of table handling experiments

Here we're starting with a complete parquet dataset NZHSM22_RLZ which is already partitioned by:
 - **vs30** (18 of these) ~ **23 Gb** each.
 - **nloc_0** the 1 degree grid (there are 64 of these in NZ)

And we're taking one permutation of these, selecting the largest case: `nloc_0 = "-40.0~176.0"` which contains 121 individual nloc_001 locations.

On disk this subpartion is **761 Mb**, and is about 3% of the complete NSHM_1.0.4 model.

## Memory mapped files

The first demo

 - `demo_mmap.py` splits  source data 
 - `demo_mmap_reader.py` reads from the mmap file.

This offers little benefit in our situation as our table sizes are small (ie they fit in memory).
Testing showed this to be slightly slower than regular files with our small tables.

## Other table formats, optimisations.

 pyarrow offers us a number of table/dataset serialisation options (parquet, orc, ipc, feather).
 - what is the minimum size on disk of the tables/vs time to round-trip serialisation.
 - what memory is required a) to split the tables, and b) for each table-handling task.

 - `demo_mmap_2.py` splits source data into data required per aggregation task.
 - `demo_mmap_reader.py` reads from the mmap file: `read_one()` and `read_all()`.

### Tests:
 
  - IPC / dataset format 
    baseline 
  - ORC  table format see https://arrow.apache.org/docs/python/orc.html
    most compatible, built in compression, fast

#### Size on disk, all the task tables

 - IPC: 2.0 Gb
 - ORC: 0.6 Gb 

#### Time to process, per task

Read in the table, convert to pandas dataframe, check dimensions = (912, 3)

 - IPC: (not measured)
 - ORC: <1ms per task 

```
chrisbc@MLX01 toshi-hazard-store % poetry run python demo/demo_mmap_reader2.py

process all

processed 3483 tables in 2.789946 at avg of 0.0008010180878552972 secs per table.
```

#### Memory required per task

the read_one() function shows us that to get a pandas dataframe with all the data loaded we needc about 100Mb per task.

```
[912 rows x 3 columns]
dataframe built  memory  103.984375  Mb
```