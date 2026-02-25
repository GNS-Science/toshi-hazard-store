# Changelog

## [1.4.2] 2026-02-25

### Added
- Documentation for PyArrow parquet-based query API:
  - New `docs/api/query/index.md` with query function overview
  - Added docs for constraint enums (`AggregationEnum`, `IntensityMeasureTypeEnum`, `VS30Enum`, `ProbabilityEnum`)

### Changed
- **Breaking change in documentation**: Replaced outdated DynamoDB-era docs with current PyArrow parquet API:
  - Rewrote `docs/usage.md` with current `get_hazard_curves()` and `get_gridded_hazard()` examples
  - Rewrote `docs/configuration.md` to reflect current environment variables (`THS_DATASET_AGGR_URI`, etc.)
  - Rewrote domain model pages to use mkdocstrings auto-generated docs from pydantic models:
    - `docs/domain_model/openquake_models.md` → now documents `HazardAggregateCurve`
    - `docs/domain_model/hazard_metadata.md` (renamed from `proposed_hazard_models.md`) → documents `CompatibleHazardCalculation`, `HazardCurveProducerConfig`
    - `docs/domain_model/gridded_hazard_models.md` → documents `GriddedHazardPoeLevels`
  - Updated `docs/cli/hazard_dataset_overview.md` and `docs/cli/aggregation_cli_workflow.md` (renamed from `usage.md`)
  - Added mkdocstrings options for consistency in model documentation
  - Fixed typo in `HazardCurveProducerConfig` docstring ("reproducablity" → "reproducibility")

### Fixed
- Added missing attributes section to `HazardCurveProducerConfig` docstring
- Fixed cookiecutter placeholder URLs in `docs/installation.md`
- Fixed various typos in documentation files
- Added empty line before markdown lists (required for mkdocs parsing)
- Added documentation conventions to `CLAUDE.md`

### Removed
- Removed commented-out nav entry `# - Parquet: TODO.md` from `mkdocs.yml`
- Removed `.DS_Store` files from docs directory

## [1.4.1] 2026-02-24

### Removed
- **Complete removal of DynamoDB/PynamoDB dependencies**:
  - Removed `pynamodb` and `pynamodb-attributes` from dependencies in `pyproject.toml`
  - Deleted `toshi_hazard_store/pynamodb_settings.py` (PynamoDB configuration)
  - Deleted entire `toshi_hazard_store/model/attributes/` module (4 files):
    - `__init__.py`, `attributes.py`, `enum_attribute.py`, `enum_constrained_attribute.py`
  - Deleted test files that tested only PynamoDB/DynamoDB functionality:
    - `tests/test_attributes.py`
    - `tests/gridded_hazard/features/test_main_features.py`
- Removed pynamodb-specific logging from `ths_rlz_import.py` and `ths_grid_build.py`

### Changed
- Updated docstrings and documentation to remove DynamoDB references:
  - `ths_grid_sanity.py`: Updated module and function docstrings
  - `ths_agg_backup.py`: Updated comment on legacy S3 path
  - `README.md`: Removed deprecated DynamoDB feature line
  - `LICENSE`: Updated description to reference parquet datasets instead of DynamoDB
  - `docs/configuration.md`: Removed AWS DynamoDB references
  - `docs/cli/index.md` and `docs/cli/usage.md`: Updated migration workflow descriptions
  - `tests/query/test_hazard_curve_migration.py`: Updated docstring and comments
  - `tests/scripts/test_ths_grid_sanity.py`: Updated test assertion text

### Fixed
- Made `nzshm_model` imports lazy in `parse_oq_realizations.py` to prevent AWS secret
  fetching at module import time (was causing test failures without AWS credentials)
- Added global AWS mocking in `tests/conftest.py` using `pytest_configure()` hook:
  - Mocks AWS Secrets Manager with dummy secrets for `nzshm_model` dependency
  - Ensures tests never use real AWS services, even when credentials are present
  - Prevents `AttributeError: 'NoneType' object has no attribute 'get'` when AWS
    secrets cannot be fetched

### Notes
- This release completes the migration away from DynamoDB started in v1.4.0
- The codebase now exclusively uses pyarrow datasets for all hazard data storage
- Historical migration documentation in `docs/migration/` is preserved for reference

## [1.4.0] 2026-02-24
### Added
- `dataset_uri` parameter to `get_hazard_curves` and all query strategy functions, allowing
  users to specify non-default dataset locations without changing environment variables
- Missing `ths_grid_sanity` CLI doc page
- Comprehensive test coverage for `get_gridded_hazard` function with 6 new tests
- New test module `tests/query/test_gridded_hazard_query.py`
- Comprehensive test coverage for all CLI scripts (26 new tests)
- **Hoisted query module exports**: `toshi_hazard_store.query` now provides unified access to:
  - Main query functions: `get_hazard_curves`, `get_gridded_hazard`
  - Data models: `AggregatedHazard`, `IMTValue`
  - Location utilities: `downsample_code`, `get_hashes`
  - Dataset cache accessors: `get_dataset`, `get_gridded_dataset`, `get_dataset_vs30`, `get_dataset_vs30_nloc0`
  - Config constants: `DATASET_AGGR_URI`, `DATASET_GRIDDED_URI`
- New comprehensive API documentation at `docs/api/query/index.md` with usage examples
- `__all__` export list in `query/__init__.py` for clean public API

### Changed
- Renamed CLI scripts for clearer naming conventions:
  - `ths_build_gridded` → `ths_grid_build`
  - `ths_import` → `ths_rlz_import`
  - `ths_ds_sanity` → `ths_rlz_sanity`
  - `ths_json_backup` → `ths_agg_backup`
- Reorganized mkdocs nav: alphabetized CLI tools, created "Data Models" section,
  nested "Legacy Migrations" under "Datasets"
- Updated project description in pyproject.toml
- Fixed docstrings in `get_hazard_curves` (missing `imts`) and `get_gridded_hazard`
- Refactored large `datasets.py` module (529 lines) into 4 focused modules:
  - `models.py` - Data models and constants (110 lines)
  - `dataset_cache.py` - Dataset caching functionality (115 lines)
  - `query_strategies.py` - Different query strategies (205 lines)
  - `datasets.py` - Main query interface (115 lines, reduced from 529)
- Updated all imports and references to use new module structure
- **Simplified query imports**: All code now uses `from toshi_hazard_store import query`
  pattern instead of deep submodule imports (`query.datasets`, `query.models`, etc.)
- Removed all unused imports from script test files
- Updated API documentation to remove references to removed modules

### Removed
- Deprecated PynamoDB model `toshi_hazard_store/model/gridded_hazard.py`
- Deprecated PynamoDB queries `toshi_hazard_store/query/gridded_hazard_query.py`
- Unused import of `get_one_gridded_hazard` from `__init__.py`
- Stale doc files: `docs/api.md`, `docs/assistant_logs/`, `docs/datasets/error.md`
- Broken `Query API` nav section (referenced deleted file)
- Legacy comments in pyproject.toml
- All gridded hazard functionality now uses pyarrow datasets instead of DynamoDB

### Fixed
- MkDocs build error caused by references to removed `gridded_hazard_query` module
- All documentation now builds successfully
- **Enabled skipped grid tests**: `test_build_and_roundtrip_gridded_dataset` in 
  `tests/model/test_hazard_grid_models.py` was failing due to incorrect import 
  (`datasets` vs `dataset_cache`) and improper `RegionGrid` mocking. Fixed by:
  - Correcting import to use `dataset_cache` module
  - Fixing monkeypatch target to patch at `dataset_cache.DATASET_AGGR_URI`
  - Properly mocking `RegionGrid` Enum with `__getitem__` return value
  - Converting `CodedLocation` objects to `(lat, lon)` tuples for mock

## [1.4.0-next-release] 2026-01
### Added
- migrated 'ths_build_grid` script, module and tests from `toshi-hazard-haste` project.
- DEVELOPMENT.md describes developer environment setup.
- gridded pydantic model
- pa schemas built from pydantic model

### Changed
- set `pyarrow <3` upper bound as the new 3.0.0. version introduces some schema issues.
- revised tox configuration for proper environment selection

## [1.3.1] 2026-01-20
### Changed
 - update dependencies for new advisories

## [1.3.0] 2025-11-25
### Added
 - new producer config `8c09bffb9f4c`

### Removed
 - PynamoDB model `hazard_aggregate_curve.HazardAggregateCurve`
 - PynamoDB model `hazard_realization_curve.HazardRealizationCurve`
 - PynamoDB model `hazard_models.CompatibleHazardCalculation`
 - PynamoDB model `hazard_models.HazardCurveProducerConfig`
 - remove disagg models and queries
 - stale workflow files

## [1.2.5] 2025-11-10
### Added
 - audit step in setup.cfg
 
### Changed
 - test skipped for AWS error, deprecated package will eventually be removed
 - migrate pyproject.toml to PEP508
 - security updates
 - CI/CD workflows use latest shared actions
 - minor typing issue ignored

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
