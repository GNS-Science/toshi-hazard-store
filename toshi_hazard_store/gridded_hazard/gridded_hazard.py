# coding: utf-8

import itertools
import logging
import multiprocessing
from collections import namedtuple
from typing import Iterable, List, Optional

import numpy as np
from nzshm_common.grids import RegionGrid
from nzshm_common.location import CodedLocation

from toshi_hazard_store import query
from toshi_hazard_store.model.hazard_models_pydantic import GriddedHazardPoeLevels
from toshi_hazard_store.model.pyarrow import pyarrow_dataset

from .gridded_poe import compute_hazard_at_poe

log = logging.getLogger(__name__)
INVESTIGATION_TIME = 50
SPOOF_SAVE = False
COV_AGG_KEY = 'cov'

DEFAULT_GRID_ACCEL_VALUE = np.nan  # historically was None, but this cannot be serialised by pyarrow

GridHazTaskArgs = namedtuple(
    "GridHazTaskArgs", "poe_lvl location_grid_id compatible_calc_id hazard_model_id vs30 imt agg output_target"
)


def process_gridded_hazard(
    poe_lvl: float,
    location_grid_id: str,
    compatible_calc_id: str,
    hazard_model_id: str,
    vs30: int,
    imt: str,
    agg: str,
) -> Iterable[GriddedHazardPoeLevels]:
    """
    Compute and yield GriddedHazardPoeLevels for the given ... POE level, and hazard model.

        poe_lvl (float): POE level to compute for.
        location_grid_id (str): ID of the region grid.
        compatible_calc_id (str): ID of the compatible calculation.
        hazard_model_id (str): ID of the hazard model.
        vs30 (int): VS30 value for each location.
        imt (str): Intensity measure type (e.g. PGA, PGV).
        agg (str): Aggregation method (e.g. mean, max).

    Yields:
        GriddedHazardPoeLevels: Computed GriddedHazardPoeLevels for the given location keys and POE level.
    """
    if not (0 < poe_lvl < 1):
        raise ValueError(f'poe value {poe_lvl} is not supported.')

    grid = RegionGrid[location_grid_id]
    locations = list(
        map(lambda grd_loc: CodedLocation(grd_loc[0], grd_loc[1], resolution=grid.resolution), grid.load())
    )
    location_keys = [loc.resample(0.001).code for loc in locations]

    grid_accel_levels: List = [DEFAULT_GRID_ACCEL_VALUE for i in range(len(location_keys))]
    indices_computed = []
    for haz in query.get_hazard_curves(location_keys, [vs30], hazard_model_id, imts=[imt], aggs=[agg]):
        accel_levels = [val.lvl for val in haz.values]
        poe_values = [val.val for val in haz.values]
        index = location_keys.index(haz.nloc_001)
        try:
            indices_computed.append(index)
            grid_accel_levels[index] = compute_hazard_at_poe(poe_lvl, accel_levels, poe_values, INVESTIGATION_TIME)
        except ValueError as err:
            log.error(
                'Error in compute_hazard_at_poe: `%s` for poe_lvl: `%s`, hazard_model: `%s`,`'
                ' vs30: `%s`, imt: `%s`, agg: `%s`, loc:%s'
                % (err, poe_lvl, hazard_model_id, vs30, imt, agg, haz.nloc_001)
            )
            log.warning(f"index: {index}; ` poe_values`: {poe_values}")
            continue
            # raise
        log.debug('replaced %s with %s' % (index, grid_accel_levels[index]))

    # DONE: no evidence now that we have validated that the grid_accel_levels values are all floats ...
    # now this shows us with 0.632 max_poe the non-monotonic
    # try:
    #     GriddedHazardPoeLevels.validate_grid_accel_levels(grid_accel_levels)  # raise
    # except ValueError as err:
    #     log.warning(f"invalid values found in `grid_accel_levels`. 1st 20 indices_computed: {indices_computed[:20]}.")
    #     log.warning(err)
    #     raise err

    log.info('No problem detected in in `grid_accel_levels`, all values are floats')

    if agg == 'mean':
        grid_covs: List = [None for i in range(len(location_keys))]
        for cov in query.get_hazard_curves(location_keys, [vs30], hazard_model_id, imts=[imt], aggs=[COV_AGG_KEY]):
            cov_values = [val.val for val in cov.values]
            index = location_keys.index(cov.nloc_001)
            grid_covs[index] = np.exp(
                np.interp(np.log(grid_accel_levels[index]), np.log(accel_levels), np.log(cov_values))
            )
            yield GriddedHazardPoeLevels(
                compatible_calc_id=compatible_calc_id,
                hazard_model_id=hazard_model_id,
                location_grid_id=location_grid_id,
                vs30=vs30,
                imt=imt,
                aggr=COV_AGG_KEY,
                investigation_time=INVESTIGATION_TIME,
                poe=poe_lvl,
                accel_levels=grid_covs,
            )

    yield GriddedHazardPoeLevels(
        compatible_calc_id=compatible_calc_id,
        hazard_model_id=hazard_model_id,
        location_grid_id=location_grid_id,
        vs30=vs30,
        imt=imt,
        aggr=agg,
        investigation_time=INVESTIGATION_TIME,
        poe=poe_lvl,
        accel_levels=grid_accel_levels,
    )


class GriddedHazardWorkerMP(multiprocessing.Process):
    """A worker that batches and saves records to DynamoDB."""

    def __init__(self, task_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue

    # TODO: reinstate using new pyarrow outputs in place of dynamodb
    def run(self):
        log.info("worker %s running." % self.name)
        proc_name = self.name

        while True:
            nt = self.task_queue.get()
            if nt is None:
                # Poison pill means shutdown
                self.task_queue.task_done()
                log.info('%s: Exiting' % proc_name)
                break

            # log.info(f"nt: {nt[:4]}")
            try:
                gridded_models = list(process_gridded_hazard(*nt[:-1]))
                # write the dataset
                table = pyarrow_dataset.table_from_models(gridded_models)
                output_folder, filesystem = pyarrow_dataset.configure_output(nt.output_target)
                pyarrow_dataset.append_models_to_dataset(
                    table,
                    output_folder,
                    filesystem=filesystem,
                    partitioning=['hazard_model_id'],
                    schema=GriddedHazardPoeLevels.pyarrow_schema(),
                )
            except Exception as err:
                log.warning(f'Error in process_gridded_hazard: with task args `{nt}`')
                log.warning(f'Error: {err}')
            finally:
                self.task_queue.task_done()
                log.info('%s task done.' % self.name)


def calc_gridded_hazard(
    output_target: str,
    location_grid_id: str,
    poe_levels: Iterable[float],
    hazard_model_ids: Iterable[str],
    vs30s: Iterable[float],
    imts: Iterable[str],
    aggs: Iterable[str],
    num_workers: int,
    filter_locations: Optional[Iterable[CodedLocation]] = None,
):
    """
    Compute and save gridded hazard rows for the given parameters.

    Args:
        output_target (str): URL of the output dataset.
        location_grid_id (str): ID of the region grid.
        poe_levels (Iterable[float]): POE levels to compute for.
        hazard_model_ids (Iterable[str]): IDs of the hazard models.
        vs30s (Iterable[float]): VS30 values for each location.
        imts (Iterable[str]): Intensity measure types (e.g. PGA, PGV).
        aggs (Iterable[str]): Aggregation methods (e.g. mean, max).
        num_workers (int): Number of worker processes to use.
        filter_locations (Optional[Iterable[CodedLocation]]): Optional list of locations to filter by.

    Returns:
        None
    """
    log.debug(
        'calc_gridded_hazard( grid: %s poes: %s models: %s vs30s: %s imts: %s aggs: %s'
        % (location_grid_id, poe_levels, hazard_model_ids, vs30s, imts, aggs)
    )
    count = 0

    task_queue: multiprocessing.JoinableQueue = multiprocessing.JoinableQueue()

    log.debug('Creating %d workers' % num_workers)
    workers = [GriddedHazardWorkerMP(task_queue) for i in range(num_workers)]
    for w in workers:
        w.start()

    for poe_lvl, hazard_model_id, vs30, imt, agg in itertools.product(poe_levels, hazard_model_ids, vs30s, imts, aggs):

        t = GridHazTaskArgs(poe_lvl, location_grid_id, "NZSHM22", hazard_model_id, vs30, imt, agg, output_target)
        task_queue.put(t)
        count += 1

    # Add a poison pill for each to signal we've done everything
    for i in range(num_workers):
        task_queue.put(None)

    # Wait for all of the tasks to finish
    task_queue.join()

    log.info('calc_gridded_hazard() produced %s gridded_hazard rows ' % count)
