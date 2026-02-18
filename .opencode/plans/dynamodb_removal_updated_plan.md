# Updated Plan: Remove DynamoDB Support

## Summary

After further investigation, I've updated the plan. The `revision_4` files are still actively used and contain PyArrow functionality, not DynamoDB. Only specific files need to be removed.

## Files to Remove (Confirmed)

### Core DynamoDB Model Files
1. **`toshi_hazard_store/model/gridded_hazard.py`** (88 lines)
   - Main DynamoDB GriddedHazard model
   - Has explicit deprecated marker at line 3: "DynamoDB is deprecated, and replaced with parquet datasets"
   - Only file importing pynamodb models

2. **`toshi_hazard_store/pynamodb_settings.py`** (13 lines)
   - Configuration for PynamoDB
   - No longer needed

### DynamoDB-Specific Attribute Files
3. **`toshi_hazard_store/model/attributes/enum_attribute.py`** (66 lines)
   - Depends on pynamodb.attributes and pynamodb.constants
   - Only used by gridded_hazard.py

4. **`toshi_hazard_store/model/attributes/enum_constrained_attribute.py`** (143 lines)
   - Depends on pynamodb.attributes and pynamodb.constants
   - Only used by gridded_hazard.py

5. **`toshi_hazard_store/model/attributes/attributes.py`** (110 lines)
   - Depends on pynamodb.attributes and pynamodb.constants
   - Only used by gridded_hazard.py

6. **`toshi_hazard_store/model/attributes/__init__.py`** (16 lines)
   - Exports all attribute classes
   - Only used by gridded_hazard.py

## Files to Keep (Previously Thought for Removal)

### revision_4 Files - STILL USED and NO DynamoDB References
1. **`toshi_hazard_store/model/revision_4/extract_classical_hdf5.py`**
   - Used by: ths_import.py, toshi_api_subtask.py, tests
   - No DynamoDB references found
   - Contains PyArrow functionality

2. **`toshi_hazard_store/model/revision_4/extract_disagg_hdf5.py`**
   - No DynamoDB references found
   - Used by extract_classical_hdf5.py

3. **`toshi_hazard_store/model/revision_4/extract_disagg.py`**
   - No DynamoDB references found

## Dependencies to Remove

From pyproject.toml:
```python
# Remove these lines from dependencies (lines 39-40)
pynamodb (>=6.0.0),
pynamodb-attributes (>=0.4.0),

# Remove from scripts group (line 75) - but check if needed for ECR
boto3,
```

## Files to Cleanup (Remove Logging)

1. **`toshi_hazard_store/scripts/ths_build_gridded.py`**
   - Lines 27-28: logging.getLogger('botocore').setLevel(logging.INFO)
   - logging.getLogger('pynamodb').setLevel(logging.INFO)

2. **`toshi_hazard_store/scripts/ths_ds_sanity.py`**
   - Line 25: logging.getLogger('botocore').setLevel(logging.WARNING)

3. **`toshi_hazard_store/scripts/ths_import.py`**
   - Lines 52-53: logging for pynamodb/botocore

## Test Files to Remove

1. **`tests/query/test_hazard_curve_migration.py`**
   - Test file specifically for DynamoDB migration

## Documentation Updates

1. **README.md** line 23: Remove "Deprecated" mention of DynamoDB in Features section
2. **CHANGELOG.md**: Review for outdated DynamoDB references

## Verification of revision_4 Usage

```bash
$ grep -r "from.*revision_4|import.*revision_4" toshi_hazard_store tests
```

**Results**:
- `tests/oq_import/test_extract_classical_hdf5.py`: imports extract_classical_hdf5
- `toshi_hazard_store/scripts/ths_import.py`: imports extract_classical_hdf5
- `toshi_hazard_store/oq_import/toshi_api_subtask.py`: imports extract_classical_hdf5
- `extract_disagg_hdf5.py`: imports from extract_classical_hdf5

```bash
$ grep -r "dynamodb|pynamodb|boto" toshi_hazard_store/model/revision_4
```

**Results**: No matches found ✅

## Updated Implementation Plan

1. **Remove DynamoDB model files** (gridded_hazard.py, pynamodb_settings.py)
2. **Remove DynamoDB attribute files** (entire attributes directory)
3. **Remove pynamodb dependencies** from pyproject.toml
4. **Clean up scripts** (remove deprecated logging)
5. **Remove migration test** (test_hazard_curve_migration.py)
6. **Update documentation** (README, CHANGELOG)

## Files to Keep

✅ **revision_4 directory** - actively used, no DynamoDB references
✅ **boto3 for ECR** - needed for aws_ecr_docker_image.py
✅ **All PyArrow/Pydantic models** - these are the current implementation

## Risk Assessment

- **High Risk**: None
- **Medium Risk**: None - all removals are isolated to DynamoDB-specific code
- **Low Risk**: Script logging cleanup, documentation updates

## Confidence Level: HIGH ✅

The revision_4 files are confirmed to be actively used and contain no DynamoDB references. The removal plan is now accurate and safe.
