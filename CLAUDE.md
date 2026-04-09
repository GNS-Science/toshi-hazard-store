# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
uv run pytest                                                    # all tests
uv run pytest tests/oq_import/test_extract_classical_hdf5.py   # single file
uv run pytest -k "test_name"                                     # single test by name
```

### Format & Lint
```bash
uv run tox -e format,lint   # ruff format + ruff check + mypy
uv run tox -e format        # ruff format + ruff check --fix (imports) only
uv run tox -e lint          # ruff check + mypy only
```

### Build & Release
```bash
uv build
bump2version patch   # updates pyproject.toml, __init__.py, creates git tag
git push && git push --tags   # triggers PyPI publish via GitHub Actions
```

## Architecture

### Layers

```
toshi_hazard_store/
├── query/          ← Public API: get_hazard_curves(), get_gridded_hazard()
├── model/          ← Pydantic models, PyArrow schemas, storage I/O
│   └── pyarrow/    ← Dataset read/write (local + S3)
├── gridded_hazard/ ← Compute gridded hazard from aggregated curves
├── oq_import/      ← Extract OpenQuake HDF5 → parquet (import pipeline)
└── scripts/        ← Click CLI entry points (ths_rlz_import, ths_grid_build, …)
```

### Query Module (`query/`)

The only public API. Three query strategies in `query_strategies.py` differ in how they partition PyArrow dataset reads — functionally equivalent, but performance varies with dataset size:

- **`naive`** — single filter across the whole dataset
- **`d1`** — iterates per-vs30 partition (good for mid-size data)
- **`d2`** — iterates per-vs30 then per-nloc_0 partition (best for large NSHM datasets / AWS Lambda)

`dataset_cache.py` wraps dataset accessors with `@lru_cache`; cache sizes are tuned (maxsize=1 for full dataset, maxsize=32 for vs30+nloc_0 partitions).

Dataset URIs come from env vars `THS_DATASET_AGGR_URI` and `THS_DATASET_GRIDDED_URI`.

### Parquet Storage Layout

Datasets use Hive-style partitioning:

```
<dataset_root>/
├── vs30=250/
│   └── nloc_0=-38.0/
│       └── <uuid>-part-0.parquet
└── vs30=400/
    └── nloc_0=-37.0/
        └── <uuid>-part-0.parquet
```

Schemas are generated dynamically from Pydantic models via `lancedb.pydantic.pydantic_to_schema()`. All hazard curves have **exactly 44 values** (validated by Pydantic).

Write path: `model/pyarrow/pyarrow_dataset.py::append_models_to_dataset()`.

### Location Codes

Locations are string codes in `"lat~lon"` format (e.g. `"-38.330~17.550"`) at three resolutions:

| Field | Resolution | Purpose |
|-------|-----------|---------|
| `nloc_001` | 0.001° | Exact query filtering |
| `nloc_0` | 1.0° | Hive partition key |
| (intermediate) | 0.1° | Secondary spatial filtering |

Use `CodedLocation` from `nzshm-common` to generate these codes via `.resample(resolution)`.

### Key Non-Obvious Patterns

**Performance reads**: `GriddedHazardPoeLevels.model_construct()` skips Pydantic validators when loading from trusted parquet data. Use the regular constructor only for user input.

**Lazy AWS imports**: `oq_import/parse_oq_realizations.py` defers `nzshm_model` imports (which call AWS Secrets Manager) until first use via an `@lru_cache` wrapper. This prevents test failures before mocking is set up.

**Dictionary arrays**: HDF5 extraction uses `pa.DictionaryArray` for low-cardinality columns (`imt`, `rlz`, digest fields) to compress data dramatically.

**Reproducibility fields**: Each curve record stores `compatible_calc_id`, `producer_digest` (Docker SHA256), and `config_digest` (OQ job config hash) for traceability.

## Code Conventions

- **Formatter**: black (line-length 120)
- **Import sorting**: isort (multi_line_output=3, force_grid_wrap=0)
- **Linting**: flake8 + mypy
- **Docstrings**: Google style for public functions

## Testing Requirements

### AWS Mocking

`tests/conftest.py::pytest_configure()` starts the `moto` mock BEFORE test collection to intercept all AWS calls. It creates fake Secrets Manager secrets for `nzshm_model`:

- `NZSHM22_TOSHI_API_SECRET_PROD`
- `NZSHM22_TOSHI_API_SECRET_TEST`

Any new dependency that calls AWS at import time must be accounted for here.

## Release Process

1. Ensure tests pass and `poetry run tox -e format,lint` passes
2. Update `CHANGELOG.md` with version header (e.g. `## [1.4.1] 2026-02-24`)
3. `bump2version patch` (or `minor`/`major`) — commits + tags automatically
4. `git push && git push --tags` — GitHub Actions publishes to PyPI

## Documentation Conventions

### MkDocs Lists

Always include an **empty line before lists** — the markdown parser silently ignores lists without one.

### Pydantic Model Docs

Use this pattern for all models in `docs/domain_model/`:

```yaml
::: toshi_hazard_store.model.hazard_models_pydantic.HazardAggregateCurve
    options:
      show_source: true
      members: false
      attributes: true
```
