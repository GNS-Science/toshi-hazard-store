# DynamoDB Removal Summary

## Files Removed

### Core DynamoDB Model Files
1. **`toshi_hazard_store/model/gridded_hazard.py`** - Main DynamoDB GriddedHazard model
2. **`toshi_hazard_store/pynamodb_settings.py`** - PynamoDB configuration

### DynamoDB Query Files
3. **`toshi_hazard_store/query/gridded_hazard_query.py`** - DynamoDB query functions

### DynamoDB Attribute Files  
4. **`toshi_hazard_store/model/attributes/__init__.py`** - Attribute exports
5. **`toshi_hazard_store/model/attributes/attributes.py`** - Custom attributes
6. **`toshi_hazard_store/model/attributes/enum_attribute.py`** - Enum attributes
7. **`toshi_hazard_store/model/attributes/enum_constrained_attribute.py`** - Constrained enum attributes

### DynamoDB Test Files
8. **`tests/query/test_hazard_curve_migration.py`** - DynamoDB migration tests

### DynamoDB Script Files
9. **`toshi_hazard_store/scripts/ths_grid_sanity.py`** - DynamoDB vs Dataset comparison script
10. **`cli_geojson` function from `toshi_hazard_store/scripts/ths_build_gridded.py`** - DynamoDB geojson command

## Dependencies Removed

From pyproject.toml:
- `pynamodb (>=6.0.0)`
- `pynamodb-attributes (>=0.4.0)`
- `boto3` from scripts group (kept for ECR functionality)

## Files Updated

### Scripts Cleanup (Removed DynamoDB logging)
1. **`toshi_hazard_store/scripts/ths_build_gridded.py`** - Removed pynamodb/botocore logging
2. **`toshi_hazard_store/scripts/ths_ds_sanity.py`** - Removed botocore logging  
3. **`toshi_hazard_store/scripts/ths_import.py`** - Removed pynamodb/botocore logging

### Query Module Updates
4. **`toshi_hazard_store/query/__init__.py`** - Updated to import PyArrow get_gridded_hazard instead of DynamoDB version

### Documentation Updates
5. **`README.md`** - Removed deprecated DynamoDB mention from Features section

## Files Kept (Important)

### PyArrow/Pydantic Models (Current Implementation)
- `toshi_hazard_store/model/gridded/gridded_hazard_pydantic.py` - PyArrow models ✅
- `toshi_hazard_store/model/hazard_models_pydantic.py` - Pydantic models ✅
- `toshi_hazard_store/model/pyarrow/` - PyArrow dataset implementations ✅

### Revision 4 Files (Still Used, No DynamoDB)
- `toshi_hazard_store/model/revision_4/extract_classical_hdf5.py` - Used by scripts ✅
- `toshi_hazard_store/model/revision_4/extract_disagg_hdf5.py` - Used by above ✅
- `toshi_hazard_store/model/revision_4/extract_disagg.py` - Used by above ✅

### Gridded Hazard Directory (PyArrow Implementation)
- `toshi_hazard_store/gridded_hazard/` - Contains PyArrow grid functionality ✅

### AWS ECR Functionality (Still Needed)
- `toshi_hazard_store/oq_import/aws_ecr_docker_image.py` - Uses boto3 for ECR ✅

## Verification

All remaining imports are correctly using:
- `toshi_hazard_store.model.gridded.gridded_hazard_pydantic` (PyArrow models)
- `toshi_hazard_store.gridded_hazard` (PyArrow grid functionality)

No files remain that import the removed DynamoDB model files.

## Impact

- **Breaking Changes**: Scripts that relied on DynamoDB functionality will no longer work
- **Benefits**: Cleaner codebase, reduced dependencies, clearer focus on PyArrow/Pydantic
- **Backwards Compatibility**: Main PyArrow functionality preserved

The removal is complete and all DynamoDB-specific code has been successfully removed from the codebase!
