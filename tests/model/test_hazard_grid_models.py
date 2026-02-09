"""
Basic model migration, structure
"""

import os
from pathlib import Path

import pyarrow.dataset as ds
import pydantic_core._pydantic_core
import pytest
from pyarrow import fs

from toshi_hazard_store.gridded_hazard import gridded_hazard
from toshi_hazard_store.model import hazard_models_pydantic
from toshi_hazard_store.model.hazard_models_pydantic import GriddedHazardPoeLevels
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.query import datasets


@pytest.mark.skip('WIP on hold, RegionGrid mocking needs work')
@pytest.mark.parametrize('use64bit', [True, False])
@pytest.mark.parametrize('validate_model', [True, False])
def test_build_and_roundtrip_gridded_dataset(
    get_one_degree_region_grid_fixture, tmp_path, monkeypatch, mocker, use64bit, validate_model
):
    aggr_folder = Path(Path(os.path.realpath(__file__)).parent.parent, 'fixtures', 'aggregate_hazard')

    monkeypatch.setattr(datasets, 'DATASET_AGGR_URI', str(aggr_folder.absolute()))
    monkeypatch.setattr(hazard_models_pydantic, "DISABLE_GRIDDED_MODEL_VALIDATOR", not validate_model)
    monkeypatch.setattr(hazard_models_pydantic, "USE_64BIT_VALUES", use64bit)

    # Setup RegionGrid Mock
    mocked_grid_class = mocker.patch("toshi_hazard_store.gridded_hazard.gridded_hazard.RegionGrid")
    mocked_grid_instance = mocked_grid_class.return_value
    mocked_grid_instance.load.return_value = get_one_degree_region_grid_fixture

    print(mocked_grid_instance.grid())

    def get_models():
        # Test helper
        gridded_models = []
        for record in gridded_hazard.process_gridded_hazard(
            # location_keys=[
            #     loc.code for loc in get_one_degree_region_grid_fixture
            # ],  # TODO this field should not be used since only valid locaion_grid should be stored to grid tables
            poe_levels=[0.02],
            location_grid_id='NZ_0_1_NB_1_1',
            compatible_calc_id='NZSHM22',
            hazard_model_id='NSHM_v1.0.4',
            vs30=400,
            imt='PGA',
            agg='mean',
        ):
            gridded_models.append(record)
        return gridded_models

    if validate_model:
        with pytest.raises(pydantic_core._pydantic_core.ValidationError):
            gridded_models = get_models()
            return
    else:
        gridded_models = get_models()
        output_folder = tmp_path / "ds"
        filesystem = fs.LocalFileSystem()

        # write the dataset
        table = pyarrow_dataset.table_from_models(gridded_models)
        pyarrow_dataset.append_models_to_dataset(
            table,
            output_folder,
            filesystem=filesystem,
            partitioning=['hazard_model_id'],
            schema=GriddedHazardPoeLevels.pyarrow_schema(),
        )

        # read it back in
        dataset = ds.dataset(output_folder, filesystem=filesystem, format='parquet', partitioning='hive')
        table = dataset.to_table()
        df = table.to_pandas()

        print(df.info())
        assert df.shape[0] == len(gridded_models)
