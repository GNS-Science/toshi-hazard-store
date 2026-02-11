"""
Console script for comparing DynamoDB grids vs new Dataset grids

Given two datasources and a set of filter arguments, iterate the first datasource grid items and
compare the corresponding item in the second. If value differnces are out-of-tolerance (OOT),
record the details for the specific locations that are OOT.
"""

import json
import logging

import click
import numpy as np
import toml
from pydantic_core import from_json

from toshi_hazard_store import query
from toshi_hazard_store.model.gridded.grid_analysis import GridDiff, GridDiffDiagnostic, GridIdentity

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

    region_grid_id = conf.get('region_grid_id')
    hazard_model_ids = conf.get('hazard_model_ids')
    imts = conf.get('imts')
    vs30s = conf.get('vs30s')
    aggs = conf.get('aggs')
    poes = conf.get('poes')

    MAX_MISSES = 10
    MAX_HITS = 0
    RTOL, ATOL = 1e-5, 1e-6
    # RTOL, ATOL = 1e-15, 1e-6

    diagnostic = GridDiffDiagnostic(atol=ATOL, rtol=RTOL, region_grid_id=region_grid_id, location_map={})

    misses, hits = 0, 0
    for ghaz_dynamo in query.get_gridded_hazard(hazard_model_ids, [region_grid_id], vs30s, imts, aggs, poes):

        grid_id = GridIdentity(
            region_grid_id=region_grid_id,
            hazard_model_id=ghaz_dynamo.hazard_model_id,
            agg=ghaz_dynamo.agg,
            imt=ghaz_dynamo.imt,
            vs30=ghaz_dynamo.vs30,
            poe=ghaz_dynamo.poe,
        )
        ds = query.datasets.get_gridded_hazard(
            dataset_uri=dataset,
            location_grid_id=region_grid_id,
            hazard_model_ids=[ghaz_dynamo.hazard_model_id],
            aggs=[ghaz_dynamo.agg],
            imts=[ghaz_dynamo.imt],
            poes=[ghaz_dynamo.poe],
            vs30s=[ghaz_dynamo.vs30],
        )
        try:
            record_arrow = next(ds)
        except StopIteration:
            click.echo(f'ERROR: no dataset result for entry: `{grid_id}`')
            misses += 1
            if misses >= MAX_MISSES:
                click.echo('ABENDING after {misses} misses.')
                break
            else:
                continue

        _A = np.array(ghaz_dynamo.grid_poes).astype('float')  # old gridded hazard field was poorly named
        _B = np.array(record_arrow.accel_levels).astype('float')

        diff = GridDiff(grid_id=grid_id, l_values=_A, r_values=_B)
        mesg = diagnostic.check_diff(diff)

        if mesg:
            hits += 1
            click.echo(mesg)

        if MAX_HITS and hits >= MAX_HITS:
            click.echo(f'ABENDING after {misses} misses.')
            # print(repr(diagnostic))
            # # print(diagnostic.location_map)
            # print(f'{len(diagnostic.location_map)} locations with errors: {diagnostic.location_map.keys()}')
            jsonobj = json.dumps(diagnostic.model_dump_json(indent=2))
            # print( from_json(jsonobj))
            # print()
            newobj = GridDiffDiagnostic.model_validate_json(from_json(jsonobj), by_name=True)
            print(repr(newobj))
            break

        if hits % 2 == 0:
            with open('grid_analysis.wip.json', 'w') as fp:
                json.dump(diagnostic.model_dump(), fp, indent=2)

    with open('grid_analysis.json', 'w') as fp:
        json.dump(diagnostic.model_dump(), fp, indent=2)

    click.echo('DONE')


if __name__ == "__main__":
    main()
