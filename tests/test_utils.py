# import pytest

from nzshm_common.grids.region_grid import load_grid
from nzshm_common.location.code_location import CodedLocation


def test_load_wlg_0_005():
    grid = load_grid('WLG_0_05_nb_1_1')
    assert len(grid) == 62

    # print(grid)
    loc = CodedLocation(*grid[0])
    print(f'loc {loc}')
    print(f'resampled {loc.downsample(10)}')
    assert 0
