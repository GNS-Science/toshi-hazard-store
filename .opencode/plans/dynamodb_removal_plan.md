# DynamoDB to PyArrow/Pydantic Refactoring Plan

## Context

The toshi-hazard-store library currently uses DynamoDB with PynamoDB models for hazard storage. Based on the README (line 23) indicating DynamoDB support is deprecated, and the extensive use of PyArrow/Pydantic models in the codebase, this plan outlines how to fully remove DynamoDB support.

## Files to Remove

### Core DynamoDB Model Files
1. **`toshi_hazard_store/model/gridded_hazard.py`** (88 lines)
   - Main DynamoDB GriddedHazard model (line 26)
   - Deprecated in favor of PyArrow/Pydantic models
   - Has explicit deprecated marker at line 3

2. **`toshi_hazard_store/pynamodb_settings.py`** (13 lines)
   - Configuration for PynamoDB
   - No longer needed

### Deprecated Revision 4 Files
3. **`toshi_hazard_store/model/revision_4/extract_classical_hdf5.py`**
4. **`toshi_hazard_store/model/revision_4/extract_disagg_hdf5.py`**
5. **`toshi_hazard_store/model/revision_4/extract_disagg.py`**
   - All in revision_4 directory
   - Marked as "migrate_v3_to_v4 module (dynamodb specific)" in CHANGELOG

## Files to Refactor

### Attribute Modules (DynamoDB-Specific Dependencies)
1. **`toshi_hazard_store/model/attributes/attributes.py`**
   - Depends on pynamodb.attributes (lines 9-16)
   - Uses pynamodb.constants (line 17)
   - **Decision**: Remove all pynamodb dependencies since these are only used by DynamoDB

2. **`toshi_hazard_store/model/attributes/enum_attribute.py`**
   - Depends on pynamodb.attributes (line 7)
   - Depends on pynamodb.constants (line 8)
   - **Decision**: Remove entirely since it's only for DynamoDB

3. **`toshi_hazard_store/model/attributes/enum_constrained_attribute.py`**  
   - Depends on pynamodb.attributes (line 7)
   - Depends on pynamodb.constants (line 8)
   - **Decision**: Remove entirely since it's only for DynamoDB

4. **`toshi_hazard_store/model/attributes/__init__.py`**
   - Exports all attribute classes
   - **Decision**: Remove all enum-related exports

### Scripts Cleanup
1. **`toshi_hazard_store/scripts/ths_build_gridded.py`**
   - Lines 27-28: logging.getLogger('botocore').setLevel(logging.INFO)
   - logging.getLogger('pynamodb').setLevel(logging.INFO)
   - **Decision**: Remove these logging lines

2. **`toshi_hazard_store/scripts/ths_ds_sanity.py`**
   - Line 25: logging.getLogger('botocore').setLevel(logging.WARNING)
   - **Decision**: Remove this logging line

3. **`toshi_hazard_store/scripts/ths_import.py`**
   - Lines 52-53: logging for pynamodb/botocore
   - **Decision**: Remove these logging lines

### Test Files
1. **`tests/query/test_hazard_curve_migration.py`**
   - Test file specifically for DynamoDB migration: "tests to show that the dataset query drop-in replacement for the dynamodb query works OK"
   - **Decision**: Remove this test file entirely

## Dependencies to Remove

### In pyproject.toml
```python
# Remove these lines from dependencies (lines 39-40)
pynamodb (>=6.0.0),
pynamodb-attributes (>=0.4.0),

# Remove from scripts group (line 75)
boto3,
```

**Note**: Keep boto3 in AWS ECR docker image context (`toshi_hazard_store/oq_import/aws_ecr_docker_image.py`), but not in main dependencies.

## Other Considerations

### Documentation Updates
1. **README.md** (line 23): "Deprecated" mention of DynamoDB in Features section should be removed
2. **Any documentation about DynamoDB** should be removed or updated

### Python Dependencies Analysis Summary
From grep search (matches truncated at 100):
- 102 total matches for dynamodb/pynamodb/boto patterns
- Spread across: dynamodb model files, attributes modules, logging in scripts, tests, and documentation
- Main focus areas: `gridded_hazard.py`, attribute files, scripts with logging, and `test_hazard_curve_migration.py`

## Implementation Order

1. **Remove DynamoDB model files** - Quick win, low risk
2. **Remove dependencies from pyproject.toml** - Immediate dependency reduction
3. **Clean up scripts** - Remove deprecated logging configuration
4. **Remove attribute modules** - These are only used by DynamoDB
5. **Remove migration tests** - No longer needed
6. **Update documentation** - Remove deprecated references

## Risk Assessment

- **High Risk**: Nothing - DynamoDB is deprecated and only used in tests/old code
- **Medium Risk**: Attribute modules might be imported elsewhere (need to verify)
- **Low Risk**: Everything else is clearly marked as DynamoDB-related

## Verification Plan

After implementation:
- Run tests to ensure PyArrow/Pydantic models still work
- Verify no imports of removed modules
- Check that all scripts work properly
- Ensure documentation is accurate

## Questions for Implementation

1. Should we keep the pynamodb_settings.py file for backwards compatibility or remove it entirely?
2. Should we verify no other files import the attribute modules before removing them?
3. Should we keep migration-related CHANGELOG entries or remove outdated DynamoDB references?

**Recommendation**: Proceed with complete removal of all DynamoDB-related code since the README states it's deprecated and there's a migration path to PyArrow/Pydantic models.
