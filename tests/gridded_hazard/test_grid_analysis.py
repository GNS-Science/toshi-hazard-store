import os
from pathlib import Path

# import json
# import pytest
from pydantic_core import from_json

from toshi_hazard_store.model.gridded import grid_analysis


def test_grid_analysis_from_json():
    folder = Path(Path(os.path.realpath(__file__)).parent, 'fixtures')
    src_json = Path(folder, 'grid_analysis.wip.json')

    with src_json.open('r') as jsonfile:

        jsond = from_json(jsonfile.read())
        diag = grid_analysis.GridDiffDiagnostic.model_validate(jsond)

        print(diag)

        assert diag.checked_grid_entries == 154
        assert diag.failed_grid_entries == 24
        assert len(diag.location_codes) == 3741
        assert len(diag.location_map) == 51  # Total number of locations with errors

        assert diag.location_map['-45.900~168.800'] == grid_analysis.LocationMap(
            location_code='-45.900~168.800',
            map={
                'NZ_0_1_NB_1_1:NSHM_v1.0.4:0.95:SA(10.0):150:0.02': grid_analysis.LocationDiff(
                    l_value=0.12215683300371219, r_value=0.12215183675289154
                ),
                'NZ_0_1_NB_1_1:NSHM_v1.0.4:0.95:SA(10.0):150:0.025': grid_analysis.LocationDiff(
                    l_value=0.11309810146618604, r_value=0.11309275031089783
                ),
                'NZ_0_1_NB_1_1:NSHM_v1.0.4:0.95:SA(10.0):150:0.05': grid_analysis.LocationDiff(
                    l_value=0.0865287958778021, r_value=0.08652665466070175
                ),
            },
            max_error=5.351155288213505e-06,
            grids_in_error=3,
        )
