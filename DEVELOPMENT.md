# DEVELOPMENT

### Environment setup

- clone the repo
- setup python env

```
pyenv local 3.10 3.11 3.12
uv sync --group dev
```

## Testing

`uv run pytest`

## Detox (QA standards)

`uv run tox` to run all tox checks

Or individually...

 - `uv run tox -e audit` to run security audit.
 - `uv run tox -e format` to apply formatting rules.
 - `uv run tox -e lint` to run lint checks (style and typing).
 - `uv run tox -e py310` to run tests with coverage report.
