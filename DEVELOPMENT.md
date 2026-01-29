# DEVELOPMENT

### Environment setup

- clone the repo
- setup python env

```
pyenv local 3.10 3.11 3.12
poetry env use system 
poetry sync --all-groups
```

Note that here, `poetry env use system` will ensure that no poetry-managed virtualenv is activated. Rather the `pyenv local` shims are providing the
necessary environments for both poetry and tox.

By contrast `poetry env use 3.11` expicitly activates the python 3.11 virtualenv. BUT DO NOT do this as it will override the python interpreter used by tox for tests.

NB `poetry env list` will show that the first python envionement is activated, even though it isn't!

## Auditing requirements packages

```
poetry export --all-groups > audit.txt
poetry run pip-audit -r audit.txt -s pypi --require-hashes
poetry run pip-audit -r audit.txt -s osv --require-hashes

poetry show {package-name}
```

### `safety` requires a user login registration
```
poetry run safety scan
```

## Testing 

`poetry run pytest`

## Detox (QA standards)

`poetry run tox`

Or individual steps...

 - `poetry run tox -e format` to apply formatting rules.
 - `poetry run tox -e lint` to run lint checks (style and typing).
 - `poetry run tox -e py310` to run tests with coverage report.
 
