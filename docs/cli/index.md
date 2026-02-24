These CLI tools are used to manage hazard datasets and their metadata.

Please see [Hazard dataset overview](./hazard_dataset_overview.md) for context about the hazard datasets themselves.

## Import workflow

For hazard calculations:

 - `ths_compat` to list or maintain compatablity keys (these hopefully rarely change) 
 - `ths_rlz_import producers` to ensure latest producer configs are available in THS/resources.
 - `ths_rlz_import rlzs` to extract openquake hazard curves as a parquet dataset.
 - `ths_rlz_sanity count_rlzs` to count realisations in a parquet dataset.

See [cli usage](./usage.md) for a detailed example of the above.

## Migration workflow

For migrating from older NSHM_v1.0.* calcuations
we use the same [Import workflow (see above) ](#import-workflow), then:

  - `ths_rlz_sanity random_rlz_new` to compare random hazard curves with new datasets

## Utilities:

 - `ths_defrag` to reorganise and optimise hazard datasets.
 - `ths_check` to verify equivalence of two hazard datasets
 - `ths_filter` to create a subset dataset from a larger one.
 - `ths_query` run simple queries on a hazard dataset.


## History

About the legacy storage systems.
