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
from toshi_hazard_store.model.gridded import gridded_hazard_pydantic
from toshi_hazard_store.model.gridded.gridded_hazard_pydantic import (
    GriddedHazardPoeLevels,
)
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.query import dataset_cache


@pytest.mark.parametrize("use64bit", [True, False])
@pytest.mark.parametrize("validate_model", [True, False])
def test_build_and_roundtrip_gridded_dataset(
    get_one_degree_region_grid_fixture,
    tmp_path,
    monkeypatch,
    mocker,
    use64bit,
    validate_model,
):
    aggr_folder = Path(
        Path(os.path.realpath(__file__)).parent.parent, "fixtures", "aggregate_hazard"
    )

    monkeypatch.setattr(dataset_cache, "DATASET_AGGR_URI", str(aggr_folder.absolute()))
    monkeypatch.setattr(
        gridded_hazard_pydantic, "DISABLE_GRIDDED_MODEL_VALIDATOR", not validate_model
    )
    monkeypatch.setattr(gridded_hazard_pydantic, "USE_64BIT_VALUES", use64bit)

    # Setup RegionGrid Mock - RegionGrid is an Enum accessed via __getitem__
    # Convert CodedLocation objects to (lat, lon) tuples as expected by the code
    grid_tuples = [(loc.lat, loc.lon) for loc in get_one_degree_region_grid_fixture]

    mocked_grid = mocker.MagicMock()
    mocked_grid.load.return_value = grid_tuples
    mocked_grid.resolution = 0.1

    mocked_region_grid = mocker.patch(
        "toshi_hazard_store.gridded_hazard.gridded_hazard.RegionGrid"
    )
    mocked_region_grid.__getitem__.return_value = mocked_grid

    def get_models():
        # Test helper
        gridded_models = []
        for record in gridded_hazard.process_gridded_hazard(
            # location_keys=[
            #     loc.code for loc in get_one_degree_region_grid_fixture
            # ],  # TODO this field should not be used since only valid locaion_grid should be stored to grid tables
            poe_levels=[0.02],
            location_grid_id="NZ_0_1_NB_1_1",
            compatible_calc_id="NZSHM22",
            hazard_model_id="NSHM_v1.0.4",
            vs30=400,
            imt="PGA",
            agg="mean",
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
            partitioning=["hazard_model_id"],
            schema=GriddedHazardPoeLevels.pyarrow_schema(),
        )

        # read it back in
        dataset = ds.dataset(
            output_folder, filesystem=filesystem, format="parquet", partitioning="hive"
        )
        table = dataset.to_table()
        df = table.to_pandas()

        print(df.info())
        assert df.shape[0] == len(gridded_models)
