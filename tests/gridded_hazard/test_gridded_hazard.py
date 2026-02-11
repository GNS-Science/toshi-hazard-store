#!/usr/bin/env python
"""Tests for `gridded_hazard` package."""

import os
from pathlib import Path

import pytest

from toshi_hazard_store import gridded_hazard
from toshi_hazard_store.model.gridded import gridded_hazard_pydantic
from toshi_hazard_store.model.gridded.gridded_hazard_pydantic import GriddedHazardPoeLevels
from toshi_hazard_store.query import datasets


def test_get_one_degree_df(one_degree_hazard_sample_dataframe):
    df0 = one_degree_hazard_sample_dataframe
    print(df0)
    assert df0.shape == (26, 8)
    assert df0.columns.tolist() == [
        'compatible_calc_id',
        'hazard_model_id',
        'nloc_001',
        'nloc_0',
        'imt',
        'vs30',
        'aggr',
        'values',
    ]
    assert len(df0.nloc_001.unique()) == 13


def test_get_one_degree_grid(get_one_degree_region_grid_fixture):
    grid = get_one_degree_region_grid_fixture
    print(grid)
    assert len(grid) == 13


def test_process_gridded_hazard_basic(monkeypatch):

    folder = Path(Path(os.path.realpath(__file__)).parent.parent, 'fixtures', 'aggregate_hazard')
    monkeypatch.setattr(datasets, 'DATASET_AGGR_URI', str(folder.absolute()))
    monkeypatch.setattr(gridded_hazard_pydantic, "DISABLE_GRIDDED_MODEL_VALIDATOR", True)

    gridded = []
    for record in gridded_hazard.process_gridded_hazard(
        # location_keys=[
        #     loc.code for loc in grid
        # ],  # TODO this field should not be used since only valid locaion_grid should be stored to grid tables
        poe_levels=[0.02, 0.1],
        location_grid_id='NZ_0_1_NB_1_1',
        compatible_calc_id='NZSHM22',
        hazard_model_id='NSHM_v1.0.4',
        vs30=400,
        imt='PGA',
        agg='mean',
    ):
        gridded.append(record)

    print(gridded)
    assert 'mean' in [obj.aggr for obj in gridded]
    assert 'cov' in [obj.aggr for obj in gridded]
    assert [obj.vs30 for obj in gridded] == [400, 400, 400, 400]
    assert [obj.aggr for obj in gridded] == ['cov', 'cov', 'mean', 'mean']
    assert [obj.poe for obj in gridded] == [0.02, 0.1, 0.02, 0.1]


@pytest.mark.parametrize(
    'kwargs, message',
    [
        ({'poe': 0.0}, "poe.*not supported"),
        ({'poe': 1.0}, "poe.*not supported"),
        ({'poe': 2.0}, "poe.*not supported"),
        ({'vs30': "400"}, "vs30.*not supported"),
        ({'vs30': 400.1}, "vs30.*not supported"),
        ({'imt': "VGA"}, "imt.*not supported"),
        ({'aggr': "sum"}, "aggr.*not supported"),
        ({'investigation_time': 1}, "not supported"),
        ({'accel_levels': [1, 2, 3, 4]}, "expected accel_levels to have"),
    ],
)
def test_gridded_hazard_poe_model_validations(monkeypatch, kwargs, message):

    folder = Path(Path(os.path.realpath(__file__)).parent.parent, 'fixtures', 'aggregate_hazard')
    monkeypatch.setattr(datasets, 'DATASET_AGGR_URI', str(folder.absolute()))
    monkeypatch.setattr(
        gridded_hazard_pydantic, "DISABLE_GRIDDED_MODEL_VALIDATOR", not kwargs.get('accel_levels', False)
    )

    with pytest.raises(ValueError, match=f".* {message}"):
        assert GriddedHazardPoeLevels(
            location_grid_id='NZ_0_1_NB_1_1',
            compatible_calc_id='NZSHM22',
            hazard_model_id='NSHM_v1.0.4',
            vs30=kwargs.get('vs30', 400),
            imt=kwargs.get('imt', 'PGA'),
            aggr=kwargs.get('aggr', 'mean'),
            investigation_time=kwargs.get('investigation_time', 50),
            poe=kwargs.get('poe', 0.02),
            accel_levels=kwargs.get('accel_levels', range(13)),
        )
        print(kwargs)


# TODO delete this once it's fully replaced by above
# @mock_aws
# class GriddedHazardTest(unittest.TestCase):
#     @unittest.skip("line 134 assertion failing")
#     def test_calculate_gridded_hazard(self):
#         """This test is a TDD hack, iterating on the features and testing them all in one humungous test.

#         TODO: split up this and test the parts individually.

#         """
#         # http://docs.getmoto.org/en/latest/docs/getting_started.html#recommended-usage
#         # deferred imports to ensure imported functions are mocked
#         from toshi_hazard_store import model, query  # noqa
#         from toshi_hazard_store.gridded_hazard import calc_gridded_hazard  # noqa

#         locations, vs30s, imts, aggs = get_csv_sample_ranges(csv_hazard, 200)

#         assert len(locations) == 5

#         # builing & saving the models
#         poe_levels = [0.02, 0.1]
#         location_grid_id = "NZ_0_2_NB_1_1"  # the NZ 0.2 degree grid
#         grid = RegionGrid[location_grid_id]

#         # with model.GriddedHazard.batch_write() as batch:
#         # TODO: why is calc_gridded_hazard producing flakey results - this is why tests fail
#         calc_gridded_hazard(
#             location_grid_id=location_grid_id,
#             poe_levels=poe_levels,
#             hazard_model_ids=[HAZARD_MODEL_ID],
#             vs30s=vs30s,
#             imts=imts[:2],
#             aggs=aggs[:2],
#             num_workers=1,
#             filter_locations=[loc.resample(grid.resolution) for loc in locations],
#         )

#         # time.sleep(2)
#         # test we can retrieve something
#         count = 0
#         poes = 0
#         for ghaz in query.get_gridded_hazard([HAZARD_MODEL_ID], [location_grid_id], vs30s, imts, aggs, poe_levels):
#             poes += len(list(filter(lambda x: x is not None, ghaz.grid_poes)))
#             count += 1

#         print('table scan produced %s gridded_hazard rows and %s poe levels' % (count, poes))
#         self.assertEqual(count, 8)  # 2 aggs * 2 imts * 2 poes
#         self.assertEqual(poes, 40)  # 2 aggs * 2 imts * 2 poes * 5 sites
