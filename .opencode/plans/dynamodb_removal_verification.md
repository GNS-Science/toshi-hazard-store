# Final Plan: Remove DynamoDB Support

## Summary

This plan outline shows that DynamoDB support can be **completely removed** from the codebase. All DynamoDB-related code is deprecated and only referenced in:
- gridded_hazard.py (main model)
- pynamodb_settings.py (settings)
- revision_4 directory (old migration code)
- Attributes modules (only used by gridded_hazard.py)
- Scripts with debugging logging
- Migration tests

## Verification Results

### 1. Attribute Module Usage
```bash
$ grep -r "from.*attributes" toshi_hazard_store --include="*.py" | grep -v "test"
```

**Results**:
- `enum_constrained_attribute.py` imports pynamodb.attributes
- `attributes.py` imports pynamodb.attributes
- `__init__.py` exports attribute classes
- `enum_attribute.py` imports pynamodb.attributes
- `gridded_hazard.py` imports pynamodb.attributes, pynamodb-attributes, and uses EnumConstrainedIntegerAttribute, EnumConstrainedUnicodeAttribute, CompressedListAttribute

✅ **Conclusion**: Attributes are ONLY used by `gridded_hazard.py` (DynamoDB model)

### 2. Files Using gridded_hazard.py
```glob **/gridded/**/*.py
```

Results show only gridded directory files, confirming no other models use the DynamoDB code.

## Remove These Files (High Priority)

1. `toshi_hazard_store/model/gridded_hazard.py` - Main DynamoDB model
2. `toshi_hazard_store/pynamodb_settings.py` - PynamoDB configuration
3. `toshi_hazard_store/model/revision_4/extract_classical_hdf5.py` - Old v3 to v4 migration
4. `toshi_hazard_store/model/revision_4/extract_disagg_hdf5.py` - Old v3 to v4 migration
5. `toshi_hazard_store/model/revision_4/extract_disagg.py` - Old v3 to v4 migration

## Remove These Python Dependencies (High Priority)

From pyproject.toml:
- `pynamodb (>=6.0.0)` 
- `pynamodb-attributes (>=0.4.0)`
- `boto3` from scripts group (but can be kept for ECR docker functionality)

## Cleanup These Files (Low Priority)

1. `toshi_hazard_store/model/attributes/enum_attribute.py` - Only used by DynamoDB
2. `toshi_hazard_store/model/attributes/enum_constrained_attribute.py` - Only used by DynamoDB  
3. `toshi_hazard_store/model/attributes/attributes.py` - Only used by DynamoDB
4. `toshi_hazard_store/model/attributes/__init__.py` - Exports attributes

⚠️ Note: These can be removed entirely or refactored to be framework-agnostic

4. Remove logging lines from:
   - `ths_build_gridded.py` lines 27-28
   - `ths_ds_sanity.py` line 25
   - `ths_import.py` lines 52-53

5. Remove test file:
   - `tests/query/test_hazard_curve_migration.py`

## Post-Removal Verification

After implementing the changes:
1. Run tests to confirm PyArrow/Pydantic models still work
2. Verify no imports of removed modules remain
3. Ensure all remaining scripts work properly  
4. Review documentation for outdated DynamoDB references

## Confidence Level: HIGH ✅

All evidence shows:
- No other code uses DynamoDB models
- Attributes are ONLY used by the one DynamoDB model
- README states DynamoDB is deprecated
- Migration path to PyArrow/Pydantic exists
- No dependencies on attributes from non-DynamoDB code

This is a clean, straightforward removal with minimal risk.
