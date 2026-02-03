"""
Console script for comparing DynamoDB grids vs new Dataset grids
"""

import logging

import click
import numpy as np
import toml
from nzshm_common.grids import load_grid

from toshi_hazard_store import query

DATASET_FORMAT = 'parquet'  # TODO: make this an argument

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


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

    # count = 0
    # poe_count = 0
    for ghaz_dynamo in query.get_gridded_hazard(hazard_model_ids, [site_list], vs30s, imts, aggs, poes):

        ds = query.datasets.get_gridded_hazard(
            dataset_uri=dataset,
            location_grid_id=site_list,
            hazard_model_ids=[ghaz_dynamo.hazard_model_id],
            aggs=[ghaz_dynamo.agg],
            imts=[ghaz_dynamo.imt],
            poes=[ghaz_dynamo.poe],
            vs30s=[ghaz_dynamo.vs30],
        )
        record_arrow = next(ds)
        _A = np.array(ghaz_dynamo.grid_poes)
        _B = np.array(record_arrow.accel_levels)

        _a_nan_indices = np.where(np.isnan(_A))[0]
        _b_nan_indices = np.where(np.isnan(_B))[0]

        print(f'_a_nans: {_a_nan_indices}')
        print(f'_b_nans: {_b_nan_indices}')

        # result = np.isclose(_A, _B, rtol=1e-7, atol=1e-6)
        # if not result.all() == True:
        #     print(result, "A!!!!")
        np.testing.assert_almost_equal(_B, _A, decimal=6)

    click.echo('DONE')


if __name__ == "__main__":
    main()
