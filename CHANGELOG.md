# Changelog

## [1.2.5] 2025-09-TBC

## Added
 - Python 3.13 support

## Changed
 - upgrade nzshm-model lib (for python 3.13 support)

## Removed
 - Python 3.10 support

## [1.2.4] 2025-08
### Added
 - GHA tests: add python`3.12` and `windows-latest` to matrix.
 - more test coverage on `pyarrow` package.

### Changed
 - fixed unlink bug
 - minor test issues

## [1.2.3] 2025-08-15
### Changed
 - HDF5 extraction uses OpenQuake logic tree API solving compatibility issue with openquake-engine>=3.21.0

## [1.2.2] 2025-07-28
### Added
 - add vs30 test to `ths_ds_check.py`; fix level options;

### Changed
 - HDF5 classical extraction obtains vs30 values from HDF5. [`#99`](https://github.com/GNS-Science/toshi-hazard-store/issues/99)
   This supports hazard with site-specific vs30 and regular jobs. 
 - use hdf5 column names rather than indexes to extract site info.
 - move shell scripts out of docs;
 - fix ths_ds_sanity check;
 - move shell scripts;
 - make time cmd configurable;

## [1.2.1] 2025-07-22
### Changed
 - use pyarrow module to get correct filesystem type
 - retain og error info for deferred errors
 - improve debug logging
 - fix dataset query failure when location resolution is not `nloc_001`

### Added
 - new script for checking aggregate datasets `check_aggs_exist.py`

## [1.2.0] 2025-07-22
### Added
 - new function `toshi_hazard_store.query.datasets.get_hazard_curves` 
   for compatibility with legacy dynamodb queries. [`#121`](https://github.com/GNS-Science/toshi-hazard-store/issues/121)

## [1.1.3] 2025-07
### Changed

 - missed dataset exceptions are now deferred [`#120`](https://github.com/GNS-Science/toshi-hazard-store/issues/120)

## [1.1.2] 2025-07-07

### Changed
 - testing dataset query options
 - add missing nloc_0 arg to dataset queries 

### Added
 - testing script and docs for `pyiceberg\S3` Table support

## [1.1.1] 2025-06-27
### Added
 - new `toshi_hazard_store.query.datasets` module 
 - new dataset query types for AWS lambda usage.

## [1.1.0] 2025-06-06

### Added
 - pydantic model `HazardAggregateCurve` for use in client libs
 - new package `toshi_hazard_store.model.pyarrow`.
 - dataset schemas moved into module in `toshi_hazard_store.model.pyarrow.dataset_schema`

### Changed
 - `ths_ds_sanity count-rlz` command uses partitioning scheme for grouping.
 - `model.pyarrow.pyarrow_aggr_dataset` migrated from dynamodb to pydantic model.
 - dataset schema changes for aggregate and realisations.
 
## [1.0.0] 2025-05-20

The `1.0.0` release incorporating pyarrow dataset features from pre-release branch.

Note that this release still incorporates Dynamodb support, which will be removed in`v2.0.0`.

## [1.0.0-alpha-0]
### Added
 - local json storage with pydantic models CompatibleHazardCalculation, HazardCurveProducerConfig.
 - `ths_compat` cli script to maintain CompatibleHazardCalculation models.
 - `ths_ds_check` cli script to compare two parquet dataset.
 - added `ths_import` `store-hazard` job.
 - support writing parquet directly to S3:// URIs in `ths_import` script.
 - make `ths_import.store_hazard` usable via import.
 - `S3://` URI support to `ths_ds_defrag` and `ths_ds_sanity` scripts.
 
### Changed
 - import script `ths_import` uses new json storage classes for meta tables.
 - improved `ths_ds_check` script.
 - improved `ths_ds_sanity` script.
 - improved `ths_ds_defrag` script.
 - update to `nzshm-model 0.13.6`.
 - update `pytest`.
 - import handles all known legacy config types.

### Removed
 - v3 -> v4 migration code.
 - use of DynamoDB for V4+ models.
 - ths_r4_migrate script.
 - store_hazard_v4 script.
 - migrate_v3_to_v4 module (dynamodb specific).
 - sanity_csv_vs_hdf5.py module.
 - export_rlzs_v3() method and tests.
 - saving any model to DynamoDB.
 - removed `scripts` installer option.

## [1.0.0-alpha]
### Removed
 - support for local storage (sqlite)
 - support for local cache
 - db_adapter

### Changed
 - AWS dynamodb storage is deprecated

## [0.9.1] - 2025-03-19
### Changed
 - upgrade openquake-engine@3.20.1
 - upgrades pandas, numpy, numba, pyarrow
 - script fixes for latest nzshm-common

### Added
 - more dataset checking options

## [0.9.0] - 2024-05-27
### Added
 - V4 epic tables
 - parquet support
 - new scripts:
     - ths_r4_filter_dataset
     - ths_r4_import
     - ths_r4_migrate
     - ths_r4_query
     - migration/ths_r4_sanity
 - extract datasets directly from hdf5
 - more documtention

### Changed
  - switch to nzshm-common#pre-release branch
  - switch to nzshm-model#pre-release branch
  - move outdated scripts to scripts/legacy
  - new documentation theme

## [0.8.0] - 2024-02
### Added
 - db_adapter architecture
 - sqlite3 as db_adapter for localstorage option
 - new envionment varisbale for localstorage
 - more documentation
 - use tmp_path for new localstorage tests
 - db_adapter supports SS field type
 - dynamodb unique behaviour implement in sqlite
 - support for .env configuration (using python-dotenv)

### Changed
  - update openquake dependency for NSHM GSIMs
  - drop python 3.8 and update deps for openquake
  - more test coverage
  - refactor tests to use temporary folders correctly
  - migrated to pynamodb>=6.0

## [0.7.9] - 2024-02-26
### Changed
 - dependencies for compatibility with openquake-engine v3.19

## [0.7.8] - 2024-01-31
### Added
 - 0.5% in 50 years PoE for disaggregations

## [0.7.7] - 2023-12-13
### Changed 
 - fix publication workflow
 
## [0.7.6] - 2023-12-07
### Changed
 - update pandas dependency to ~2.0.3

## [0.7.5] - 2023-08-21
### Changed
 - faster queries for THS_OpenquakeMeta table

## [0.7.4] - 2023-08-17
### Changed
 - faster queries for THS_OpenquakeRealization table

## [0.7.3] - 2023-08-15
### Removed
 - support for python 3.8

### Changed
 - faster queries for THS_HazardAggregation table
 - query optimisation to gridded_hazard_query
 - query optimisation to disagg_querys
 - mypy 1.5.0
 - pynamodb 5.5.0
 - update mkdocs toolchain
 - GHA scripts install with `--extra openquake`

### Added 
 - ths_testing script for evaluation of performance changes
 - python 3.11
  
## [0.7.2] - 2023-04-24
### Changed
- use poetry 1.4.2 for release build workflow

## [0.7.1] - 2023-04-24
### Changed
- update nzshm-common dependency 0.6.0
- mock cache when testing hazard aggregation query

### Removed
- remove version control for ToshiOpenquakeMeta

## [0.7.0] - 2023-04-17
### Changed
 - update openquake dependency 3.16
 - update nzshm-common dependency 0.5.0
 - fix SA(0.7) value

### Added
 - script ths_cache to prepopulate and test caching
 - local caching feature
 - more spectral periods in constraint enum
 - new constraints to existing THS models
 - fix enum validations and apply to model fields
### Removed
  - remove v2 type options from batch save

## [0.6.0] - 2023-02-15
### Changed
 - refactor model package
 - refactor model.attributes package
 - more test coverage
### Added
 - two new models for DisaggAggregations
 - validation via Enum for aggregation values
 - new enumerations and constraints for probabilities, IMTS and VS30s

## [0.5.5] - 2022-10-06
### Changed
 - fix for queries with mixed length vs30 index keys
 - migrate more print statements to logging.debug

## [0.5.4] - 2022-09-27
### Added
 - new query get_one_gridded_hazard
 - -m option to script to export meta tables only
### Changed
 - migrated print statements to logging.debug
 - removed monkey patch for BASE183 - it iss in oqengine 3.15 now
 - more test cover

## [0.5.3] - 2022-08-18
### Changed
 - using nzshm-common==0.3.2 from pypi.
 - specify poetry==1.2.0b3 in all the GHA yml files.

## [0.5.1] - 2022-08-17
### Added
 - THS_HazardAggregation table support for csv serialisation.
### Changed
 - refactoring/renaming openquake import modules.
### Removed
 - one openquake test no longer works as expected. It's off-piste so skipping it for now.
 - data_functions migrated to THP
 - branch_combinator migrated to THP

## [0.5.0] - 2022-08-03
### Added
 - V3 THS table models with improved indexing and and performance (esp. THS_HazardAggregation table)
 - using latest CodedLocation API to manage gridded lcoations and resampling.
### Removed
 -  realisation aggregration computations. These have moving to toshi-hazard-post

## [0.4.1] - 2022-06-22
### Added
 - multi_batch module for parallelised batch saves
 - DESIGN.md capture notes on the experiments, test and mods to the package
 - new switch on V2 queries to force normalised_location_id
 - new '-f' switch on store_hazard script to force normalised_location_id
 - lat, lon Float fields to support numeric range filtering in queries
 - created timestamp field on stas, rlzs v2
 - added pynamodb_attributes for FloatAttribute, TimestampAttribute types

### Changed
 - V2 store queries will automatically use nomralised location if custom sites aren't available.
 - refactored model modules.

## [0.4.0] - 2022-06-10
### Added
 - new V2 models for stats and rlzs.
 - new get_hazard script for manual testing.
 - extra test coverage with optional openquake install as DEV dependency.

### Changed
 - meta dataframes are cut back to dstore defaults to minimise size.

## [0.3.2] - 2022-05-30
### Added
 - meta.aggs attribute
 - meta.inv_tme attribute

### Changed
 - store hazard can create tables.
 - store hazard adds extra meta.
 - store hazard truncates values for rlz and agg fields.
 - make stats & rlz queries tolerant to ID-only form (fails with REAL dynamodb & not in mocks).

## [0.3.1] - 2022-05-29
### Changed
 - updated usage.

## [0.3.0] - 2022-05-28
### Added
 - store_hazard script for openquake systems.
### Changed
 - tightened up model attributes names.

## [0.2.0] - 2022-05-27
### Added
 - query api improvements
 - added meta table
 - new query methods for meta and rlzs

### Changed
 - moved vs30 from curves to meta
 - updated docs

## [0.1.3] - 2022-05-26
### Changed
 - fixed mkdoc rendering of python & markdown.


## [0.1.2] - 2022-05-26
### Changed
 - fix poetry lockfile

## [0.1.1] - 2022-05-26
### Added
 - First release on PyPI.
 - query and model modules providing basic support for openquake hazard stats curves only.
