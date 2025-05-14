## Historic hazard curve extraction

Here we demonstrate the end to end workflow for importing hazard curves from the NSHM_v1.0.4
 calculations performed in 2022/2023.

The following steps process a single GeneralTask (GT). Usually a GT this would include a subtask 
 for each logictree branch in the model (49 subtasks for the NSHM).

### Step 1. Check Hazard curve compatability. 

We want to ensure there's a suitable **CompatibleHazardConfig** for these curves and obtain the identifier.

**List the identifiers**

```bash
$ poetry run ths_compat ls
NZSHM22
```

**List the identifiers, along with their metatdata**

```bash
$ poetry run ths_compat ls -v
NZSHM22 2025-03-26T01:45:19+00:00 2025-03-26T01:45:19+00:00 `Openquake hazard calculation standard from openquake-engine>=3.16 as used in NSHM_v1.*`
```

At present we have but a single identifier: `NZSHM22`

### Step 2. Check/create Hazard Curve Producers.

Now we need to find the **General Task (GT)** Identifier from Toshi API, which is used to obtain the
 historic calculation data (as HDF5 format) and additional metadata about the openquake configuration.

The General Task ID below is `R2VuZXJhbFRhc2s6NjkzMTg5Mg==` [see in Weka](http://nzshm22-weka-ui-test.s3-website-ap-southeast-2.amazonaws.com/GeneralTask/R2VuZXJhbFRhc2s6NjkzMTg5Mg==).

```bash
$ AWS_PROFILE=chrisbc poetry run ths_import producers R2VuZXJhbFRhc2s6NjkzMTg5Mg== NZSHM22 -W ./WORKING/
...
```

### Step 3. Extract hazard curves to a local dataset.


#### Either A, with location partitioning

```bash
AWS_PROFILE=chrisbc poetry run ths_import extract R2VuZXJhbFRhc2s6NjkzMTg5Mg== NZSHM22 -W ./WORKING/ -O ./WORKING/ARROW/DS1 -v
```

#### OR B, with calculation_id partitioning

```bash
AWS_PROFILE=chrisbc poetry run ths_import extract R2VuZXJhbFRhc2s6NjkzMTg5Mg== NZSHM22 -W ./WORKING/ -O ./WORKING/ARROW/DS2 -v -CID
```

### Step 3. Sanity checks

#### Check count integrity, ensuring that the number of realisations is consistent

```bash
 poetry run ths_ds_sanity count-rlz ./WORKING/ARROW/DS1 -x
```

#### Check random realisations vs DynamoDB (for existing calcs only)

This needs work, as currently the GT is not configurable, and it is needed to extract the correct metadata from the API for 
building the random queries.

### Step 4. Defrag

```bash
poetry run ths_ds_defrag ./WORKING/ARROW/DS1 ./WORKING/ARROW/DS1_DFG -p 'vs30,nloc_0' -v
```

#### check count integrity, ensure the number of realisations is consistent

```bash
poetry run ths_ds_sanity count-rlz ./WORKING/ARROW/DS1_DFG -x -v
```

### Step 5. Dataset comparison

 - similar to ths_sanity but dataset vs dataset, instead of dataset vs dynamodb.
 - useful if you have two defragged datasets and want to check that they contain the same  data
 - NB currently this just does random tests, you can set how many

```bash
poetry run ths_ds_check rlzs ./WORKING/ARROW/DS1_DFG/ ./WORKING/ARROW/DS2_DFG/ -l2 -x -v
```

Or for just one calculation ...

```
poetry run ths_ds_check rlzs ./WORKING/ARROW/DS1_DFG/ ./WORKING/ARROW/DS2_DFG/ -l2 -x -v -n 5 -cid T3BlbnF1YWtlSGF6YXJkU29sdXRpb246NjkzMTg5NA==
```

### DEMO (with both local and S3 filesystems)

Note that local file paths `./WORKING/ARROW/DSR-DEMO` below may be replaced with a valid S3 bucket/prefix e.g `s3://ths-poc-arrow-test/DSR-DEMO`.

In both cases that part of the path is the folder, which for targets, will be created if it doesn't exist.

## Prep the producer

`AWS_PROFILE=chrisbc poetry run ths_import producers R2VuZXJhbFRhc2s6NjkzMTg5Mg== NZSHM22 -W ./WORKING/ -v`

## A Runzi workflow example

This is what happens automated in hazard task logic.

`poetry run ths_import store-hazard ./WORKING/runzi/calc_2.hdf5 ./WORKING/runzi/oq_config.json NZSHM22 calcS_T "sha256:e8b44b806570dcdc4a725cafc2fbaf6dae99dbfbe69345d86b3069d3fe4a2bc6"  ./WORKING/ARROW/DSR`

The DSR dataset produced will by partioned by the Toshi ID for the Hazard task, ensuring no dataset collisions

## Historic (ToshiAPI ) workflow

Here we're processing existing hazard task outputs from the given GeneralTask (GT) to build our parquet dataset.

`AWS_PROFILE=chrisbc poetry run ths_import extract R2VuZXJhbFRhc2s6NjkzMTg5Mg== NZSHM22 -W ./WORKING/ -O ./WORKING/ARROW/DST -v`

`poetry run ths_ds_sanity count-rlz -D ./WORKING/ARROW/DST -R ALL -x -v`

## Compact / conform workflows

`poetry run ths_ds_defrag ./WORKING/ARROW/DSR ./WORKING/ARROW/DSR_DFG -p 'vs30,nloc_0' -v`
`poetry run ths_ds_defrag ./WORKING/ARROW/DST ./WORKING/ARROW/DST_DFG -p 'vs30,nloc_0' -v`


### NOW a full size GT


1) check/update the producers ....
`poetry run ths_import producers R2VuZXJhbFRhc2s6MTMyODQxNA== NZSHM22 -v -W ./WORKING`

2) extract rlz ...
`poetry run ths_import extract R2VuZXJhbFRhc2s6MTMyODQxNA== NZSHM22 -W ./WORKING/ -O ./WORKING/ARROW/DST-R2VuZXJhbFRhc2s6MTMyODQxNA==`

3) Defrag ...
`poetry run ths_ds_defrag ./WORKING/ARROW/DST-R2VuZXJhbFRhc2s6MTMyODQxNA== ./WORKING/ARROW/DST-R2VuZXJhbFRhc2s6MTMyODQxNA==_DFG`

4) Check total realizations ...
`poetry run ths_ds_sanity count-rlz ./WORKING/ARROW/DST-R2VuZXJhbFRhc2s6MTMyODQxNA==_DFG -x -v`

5) Random rlz curve comparisons to Dynamodb store ...
`poetry run ths_ds_sanity random-rlz-new ./WORKING/ARROW/DST-R2VuZXJhbFRhc2s6MTMyODQxNA==_DFG -v -df`
