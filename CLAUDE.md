# CLAUDE.md - Project Context for AI Assistants

This file provides project-specific context for AI assistants (Claude Code, opencode, etc.) working on this codebase.

## Project Overview

- **Name**: toshi-hazard-store
- **Type**: Python library (PyPI package)
- **Description**: Library for saving and retrieving NZHSM openquake hazard results using pyarrow with parquet format
- **Python**: Requires Python >=3.10, <4.0

## Development Commands

### Testing
```bash
# Run all tests (requires AWS mocking via conftest.py)
poetry run pytest

# Run specific test file
poetry run pytest tests/oq_import/test_extract_classical_hdf5.py

# Run with different (unprivileged) AWS profile (should still pass due to mocking)
AWS_PROFILE=default poetry run pytest
```

### Format & Lint
```bash
# Run format and lint checks
poetry run tox -e format,lint

# Run individually
poetry run tox -e format   # isort + black
poetry run tox -e lint     # flake8 + mypy
```

### Version Bumping
```bash
# Bump version (updates pyproject.toml, __init__.py, creates git tag)
bump2version patch  # 1.4.0 -> 1.4.1
bump2version minor  # 1.4.0 -> 1.5.0
bump2version major  # 1.4.0 -> 2.0.0
```

### Other Development
```bash
# Install dependencies
poetry install

# Sync dependencies 
poetry sync

# Run specific tox environment
poetry run tox -e py311  # Test with Python 3.11

# Build package
poetry build
```

## Code Conventions

### Style
- **Formatter**: black (line-length 120)
- **Import sorting**: isort (multi_line_output=3, force_grid_wrap=0)
- **Linting**: flake8
- **Type checking**: mypy

### Key Patterns
- Use `from toshi_hazard_store import query` for query module access
- All public APIs should have type hints
- Docstrings for public functions (Google style)
- Tests live in `tests/` mirror the source structure

## Testing Requirements

### AWS Mocking
The project uses `moto` for AWS service mocking. A global mock is set up in `tests/conftest.py` via `pytest_configure()` hook:

- Mocks AWS Secrets Manager with dummy secrets for `nzshm_model` dependency
- Tests should NEVER make real AWS calls
- Secrets created:
  - `NZSHM22_TOSHI_API_SECRET_PROD`
  - `NZSHM22_TOSHI_API_SECRET_TEST`

## Important Files

- `pyproject.toml` - Project configuration, dependencies, entry points
- `CHANGELOG.md` - Release notes (follows Keep a Changelog format)
- `LICENSE` - AGPL-3.0-or-later
- `tests/conftest.py` - Global test configuration including AWS mocking
- `toshi_hazard_store/__init__.py` - Version (`__version__`) and public exports
- `toshi_hazard_store/query/` - Main query API module

## Release Process

1. Make changes and ensure tests pass
2. Run `poetry run tox -e format,lint` - must pass
3. Update CHANGELOG.md with version header (e.g., `## [1.4.1] 2026-02-24`)
4. Run `bump2version patch` (or minor/major as appropriate) - **MANUAL**
5. Push changes and tag: `git push && git push --tags` - **MANUAL**
6. GitHub workflow automatically builds and publishes to PyPI - **AUTOMATED**

## Dependency Notes

### Key Dependencies
- **pyarrow**: Data storage format (parquet datasets)
- **pandas**: Data manipulation
- **pydantic**: Data validation
- **nzshm-model**: NZSHM-specific models and logic
- **moto**: AWS mocking for tests (in dev dependencies)

## Architecture

### Query Module
The `toshi_hazard_store.query` module provides unified access to:
- `get_hazard_curves()` - Main hazard curve query function
- `get_gridded_hazard()` - Gridded hazard query function
- Data models: `AggregatedHazard`, `IMTValue`
- Dataset utilities: `get_dataset()`, `get_dataset_vs30()`, etc.
- Constants: `DATASET_AGGR_URI`, `DATASET_GRIDDED_URI`

### Storage
- **Primary**: PyArrow datasets (parquet format)
- **Previously**: DynamoDB (deprecated, removed in v1.4.1), SQLLite (long ago)

## Common Tasks

### Adding a new CLI script
1. Create module in `toshi_hazard_store/scripts/`
2. Add entry point in `pyproject.toml` `[project.scripts]`
3. Add tests in `tests/scripts/`
4. Document in `docs/cli/`

### Adding new query functionality
1. Add to `toshi_hazard_store/query/query_strategies.py`
2. Export from `toshi_hazard_store/query/__init__.py`
3. Add tests in `tests/query/`
4. Update docs in `docs/api/query/`
