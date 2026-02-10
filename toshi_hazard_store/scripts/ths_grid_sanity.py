"""
Console script for comparing DynamoDB grids vs new Dataset grids
"""

import logging

import click
import numpy as np
import numpy.ma as ma
import toml
from nzshm_common.grids import load_grid

from toshi_hazard_store import query

DATASET_FORMAT = 'parquet'  # TODO: make this an argument

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.WARN)


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|
#
@click.group()
def main():
    """Console script comparing DynamoDB grids vs new Dataset grids."""


@main.command(name='diff')
@click.argument('DATASET')
@click.argument('CONFIG', type=click.Path(exists=True))  # help="path to a valid configuration file."
def cli_diff(config, dataset):
    """Compare grids from DynamoDB vs DATASET using CONFIG"""

    conf = toml.load(config)

    site_list = conf.get('site_list')
    hazard_model_ids = conf.get('hazard_model_ids')
    imts = conf.get('imts')
    vs30s = conf.get('vs30s')
    aggs = conf.get('aggs')
    poes = conf.get('poes')

    grid = load_grid(site_list)
    click.echo(f"Grid {site_list} has {len(grid)} locations")

    MAX_MISSES = 1000
    RTOL, ATOL = 1e-5, 1e-6
    misses = 0
    for ghaz_dynamo in query.get_gridded_hazard(hazard_model_ids, [site_list], vs30s, imts, aggs, poes):

        entry = (
            f'{site_list}, {ghaz_dynamo.hazard_model_id}, {ghaz_dynamo.agg}, {ghaz_dynamo.imt}, '
            f'{ghaz_dynamo.vs30}, {ghaz_dynamo.poe}',
        )

        ds = query.datasets.get_gridded_hazard(
            dataset_uri=dataset,
            location_grid_id=site_list,
            hazard_model_ids=[ghaz_dynamo.hazard_model_id],
            aggs=[ghaz_dynamo.agg],
            imts=[ghaz_dynamo.imt],
            poes=[ghaz_dynamo.poe],
            vs30s=[ghaz_dynamo.vs30],
        )
        try:
            record_arrow = next(ds)
        except StopIteration:
            click.echo(f'ERROR: no dataset result for entry: `{entry}`')
            misses += 1
            if misses >= MAX_MISSES:
                click.echo('ABENDING after {misses} misses.')
                break
            else:
                continue

        _A = np.array(ghaz_dynamo.grid_poes).astype('float')  # old gridded hazard field was poorly named
        _B = np.array(record_arrow.accel_levels).astype('float')

        # A. Difference detection (numeric)
        # NBwe're using masked_invalid() to mask any NaN values from the diff calcs
        _ma, _mb = ma.masked_invalid(_A), ma.masked_invalid(_B)
        result = np.isclose(_ma, _mb, rtol=RTOL, atol=ATOL)
        abs_diff = _ma - _mb
        rel_diff = abs_diff / _ma

        if not result.all():
            # print some info about the failures ...
            click.echo(
                f"DIFF: `{entry}` has {len(result) - np.count_nonzero(result)} failures,"
                f" with rtol: `{RTOL}` and atol: `{ATOL}`"
                f" max abs err: {round(abs_diff.max(),8)}, max rel err: {round(rel_diff.max(),8)}"
            )

        # B. NaN detection
        _a_nan = np.argwhere(np.isnan(_A))
        _b_nan = np.argwhere(np.isnan(_B))

        if (_a_nan.size + _b_nan.size) > 0:
            click.echo(
                f"DIFF: `{entry}` nan value(s) detected: DynamoDB: {np.count_nonzero(_a_nan)}"
                f" Dataset: {np.count_nonzero(_b_nan)}"
            )

    click.echo('DONE')


if __name__ == "__main__":
    main()
