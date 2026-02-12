"""
Console script for comparing DynamoDB grids vs new Dataset grids

Given two datasources and a set of filter arguments, iterate the first datasource grid items and
compare the corresponding item in the second. If value differnces are out-of-tolerance (OOT),
record the details for the specific locations that are OOT.
"""

import itertools
import json
import logging

import click
import numpy as np
import toml
from pydantic_core import from_json
from tqdm import tqdm

from toshi_hazard_store import query
from toshi_hazard_store.model.gridded.grid_analysis import (
    GridDiff,
    GridDiffDiagnostic,
    GridIdentity,
    LocationDiffDetail,
)

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


@main.command(name='iterate')
@click.argument('DATASET')
@click.argument('CONFIG', type=click.Path(exists=True))  # help="path to a valid configuration file."
def cli_iterate(config, dataset):
    """check DATASET has everything in CONFIG"""

    conf = toml.load(config)

    region_grid_id = conf.get('site_list')
    hazard_model_ids = conf.get('hazard_model_ids')
    imts = conf.get('imts')
    vs30s = conf.get('vs30s')
    aggs = conf.get('aggs')
    poes = conf.get('poes')

    expected_total = len(list(itertools.product(hazard_model_ids, imts, vs30s, aggs, poes)))
    count = 0

    ds = query.datasets.get_gridded_hazard(
        dataset_uri=dataset,
        location_grid_id=region_grid_id,
        hazard_model_ids=hazard_model_ids,
        aggs=aggs,
        imts=imts,
        poes=poes,
        vs30s=vs30s,
    )

    for itm in tqdm(ds, total=expected_total):
        count += 1

    assert count == expected_total


@main.command(name='diff')
@click.argument('DATASET')
@click.argument('CONFIG', type=click.Path(exists=True))  # help="path to a valid configuration file."
def cli_diff(config, dataset):
    """Compare grids from DynamoDB vs DATASET using CONFIG"""

    conf = toml.load(config)

    region_grid_id = conf.get('site_list')
    hazard_model_ids = conf.get('hazard_model_ids')
    imts = conf.get('imts')
    vs30s = conf.get('vs30s')
    aggs = conf.get('aggs')
    poes = conf.get('poes')

    MAX_MISSES = 0
    MAX_HITS = 0

    RTOL, ATOL = 1e-5, 1e-6

    diagnostic = GridDiffDiagnostic(atol=ATOL, rtol=RTOL, region_grid_id=region_grid_id, location_map={}, nans_map={})

    count, misses, hits, nans = 0, 0, 0, 0
    total = len(list(itertools.product(hazard_model_ids, imts, vs30s, aggs, poes)))

    for ghaz_dynamo in tqdm(
        query.get_gridded_hazard(hazard_model_ids, [region_grid_id], vs30s, imts, aggs, poes),
        total=total,
        desc=f"Grid differences for: {ATOL} rtol: {RTOL}",
        ncols=120,
    ):

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
            if MAX_MISSES and misses >= MAX_MISSES:
                click.echo(f'ABENDING after {misses} misses.')
                break
            else:
                continue

        _A = np.array(ghaz_dynamo.grid_poes).astype('float')  # old gridded hazard field was poorly named
        _B = np.array(record_arrow.accel_levels).astype('float')

        diff = GridDiff(grid_id=grid_id, l_values=_A, r_values=_B)

        value_mesg = diagnostic.check_diff(diff)
        if value_mesg:
            hits += 1

        nans_mesg = diagnostic.check_nans(diff)
        if nans_mesg:
            nans += 1

        if MAX_HITS and hits >= MAX_HITS:
            click.echo(f'ABENDING after {misses} misses.')
            break

        count += 1
        if count % 10 == 0:
            with open('grid_analysis.wip.json', 'w') as fp:
                json.dump(diagnostic.model_dump(), fp, indent=2)

    with open('grid_analysis.json', 'w') as fp:
        json.dump(diagnostic.model_dump(), fp, indent=2)

    click.echo(f'DONE, processed {count} grids, expected {total}. Diffs: {hits}, Nans: {nans}')


@main.command(name='report')
@click.argument('GRID_DIFF_ANALYSIS_JSON', type=click.Path(exists=True))
def cli_report(grid_diff_analysis_json):
    """Report on diff output to a jsonl file"""

    with open("diff_analysis_flat.jsonl", 'w') as outfile:
        with open(grid_diff_analysis_json, 'r') as jsonfile:

            jsond = from_json(jsonfile.read())
            diag = GridDiffDiagnostic.model_validate(jsond)
            LIMIT = 0
            count = 0
            # print(help(diag.location_map.items))

            # iterate the locations
            for loc_code, lvalue in diag.location_map.items():
                # print(f'loc_code: {loc_code} has {len(lvalue.map)} errors')
                count += 1
                if LIMIT and count >= LIMIT:
                    break

                # iterate the grid_errors
                for grid_key, location_diff in lvalue.map.items():
                    gid = GridIdentity.from_idx(grid_key)
                    diff = float(location_diff.l_value or 0) - float(location_diff.r_value or 0)
                    giddict = gid.model_dump() | dict(
                        location_code=loc_code, error=diff, l_value=location_diff.l_value, r_value=location_diff.r_value
                    )
                    detail = LocationDiffDetail(**giddict)
                    outfile.write(detail.model_dump_json() + "\n")


if __name__ == "__main__":
    main()
