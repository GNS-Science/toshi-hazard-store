# Documentation Refactor Plan

**Created:** 2026-02-25
**Status:** Pending

## Problem Summary

| # | Issue | Severity |
|---|-------|----------|
| 1 | `usage.md` is entirely DynamoDB-era — references `get_hazard_metadata()`, `get_hazard_stats_curves()`, `get_hazard_rlz_curves()` which no longer exist | High |
| 2 | All 4 domain model pages use DynamoDB/PynamoDB attribute syntax (`UnicodeAttribute`, `hash_key`, `range_key`, etc.) — none of this exists in the codebase anymore | High |
| 3 | `configuration.md` references SQLite — `THS_USE_SQLITE_ADAPTER`, `THS_SQLITE_FOLDER` env vars are dead; missing current parquet env vars (`THS_DATASET_AGGR_URI`, `THS_DATASET_GRIDDED_URI`, etc.) | High |
| 4 | `installation.md` has cookiecutter template placeholders in URLs (lines 50-51) | Medium |
| 5 | `api/query/index.md` is orphaned — 99-line Query API overview not in mkdocs nav | Medium |
| 6 | Nav label says "Legacy Vanilla (DynamodDB)" (also a typo) for the usage page | Medium |
| 7 | Commented-out nav entry `# - Parquet: TODO.md` — intended replacement usage page, never written | Low |
| 8 | Domain model page titles are confusing — "New Hazard" vs "Hazard" vs "CURRENT STATE" vs "FUTURE STATE" don't reflect actual state | Medium |
| 9 | Disaggregation model page documents models that don't exist in the codebase (disagg is experimental/WIP) | Medium |

## Phase 1: High-priority content fixes

### 1.1 Rewrite `docs/usage.md`
- Replace DynamoDB-era examples with current `query.get_hazard_curves()` and `query.get_gridded_hazard()` API
- Remove `store_hazard` TODO section
- Add strategy parameter examples (`naive`, `d1`, `d2`)
- Link to API reference for details

### 1.2 Rewrite `docs/configuration.md`
- Remove `THS_USE_SQLITE_ADAPTER` and `THS_SQLITE_FOLDER`
- Add `THS_DATASET_AGGR_ENABLED`, `THS_DATASET_AGGR_URI`, `THS_DATASET_GRIDDED_URI`
- Update the example `.env` file
- Keep `NZSHM22_HAZARD_STORE_STAGE` and `NZSHM22_HAZARD_STORE_NUM_WORKERS` (still in `config.py`)
- Remove "local sqlite3" wording from intro

### 1.3 Replace domain model pages with mkdocstrings auto-generated docs
Replace hand-written PynamoDB diagrams in the 4 `docs/domain_model/` files with `:::` directives for:
- `HazardAggregateCurve`
- `CompatibleHazardCalculation`
- `HazardCurveProducerConfig`
- `GriddedHazardPoeLevels`
- Constraint enums (`AggregationEnum`, `IntensityMeasureTypeEnum`, `VS30Enum`, `ProbabilityEnum`)

Keep brief introductory context above each directive.

### 1.4 Mark disagg page as experimental
- Add an admonition (`!!! warning`) stating these models are planned/unimplemented
- Keep in nav

## Phase 2: Structural and nav fixes

### 2.1 Fix `docs/installation.md`
- Replace cookiecutter placeholder URLs (lines 50-51) with `https://github.com/GNS-Science/toshi-hazard-store`

### 2.2 Add `docs/api/query/index.md` to nav
- Add the orphaned 99-line Query API overview as the index page for the API > query section

### 2.3 Clean up `mkdocs.yml` nav
- Rename "Legacy Vanilla (DynamodDB)" to "Usage"
- Remove `# - Parquet: TODO.md`
- Rename "New Hazard"/"Hazard" labels to match actual content (e.g., "Hazard Curves", "Hazard Metadata", "Gridded Hazard", "Disaggregation (WIP)")

## Phase 3: Minor cleanup

### 3.1 Ensure model docstrings exist
Verify/add Google-style docstrings in source so mkdocstrings renders useful content:
- `toshi_hazard_store/model/hazard_models_pydantic.py`
- `toshi_hazard_store/model/gridded/gridded_hazard_pydantic.py`
- `toshi_hazard_store/model/constraints.py`

### 3.2 Remove `.DS_Store` files from docs
- 3 `.DS_Store` files found in `docs/` tree

## Execution Order

1. **Phase 3.1 first** — docstrings must exist before auto-generated pages render properly
2. **Phase 1.3** — replace domain model pages with mkdocstrings directives
3. **Phase 1.1, 1.2, 1.4** — rewrite usage and configuration, mark disagg
4. **Phase 2** — nav and structural fixes
5. **Phase 3.2** — cleanup

## Out of Scope
- Migration docs: keep as-is under "Legacy Migrations"
- Grid analysis models, query result dataclasses, PyArrow schema: not included in auto-generated docs
