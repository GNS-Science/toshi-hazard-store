"""
Console script for comparing DynamoDB grids vs new Dataset grids

Given two datasources and a set of filter arguments, iterate the first datasource grid items and
compare the corresponding item in the second. If value differnces are out-of-tolerance (OOT),
record the details for the specific locations that are OOT.
"""

import json
import logging
from typing import Optional, Union

import click
import numpy as np
import numpy.ma as ma
import toml
from nzshm_common.location import get_locations
from pydantic import BaseModel
from pydantic_core import from_json

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


class GridIdentity(BaseModel):
    region_grid_id: str
    hazard_model_id: str
    agg: str
    imt: str
    vs30: int
    poe: float

    def to_idx(self):
        return f"{self.region_grid_id}:{self.hazard_model_id}:{self.agg}:{self.imt}:{self.vs30}:{self.poe}"

    @staticmethod
    def from_idx(idx_str: str):
        idx_vals = idx_str.split(':')
        return GridIdentity(
            region_grid_id=idx_vals[0],
            hazard_model_id=idx_vals[1],
            agg=idx_vals[2],
            imt=idx_vals[3],
            vs30=int(idx_vals[4]),
            poe=float(idx_vals[5]),
        )


class GridDiff(BaseModel):
    grid_id: GridIdentity
    l_values: np.ndarray
    r_values: np.ndarray

    class Config:
        arbitrary_types_allowed = True

    def numeric_difference(self, rtol: float, atol: float) -> Optional[np.ndarray]:
        # A. Difference detection (numeric)
        # NB we're using masked_invalid() to mask any NaN values from the diff calcs
        _ma, _mb = ma.masked_invalid(self.l_values), ma.masked_invalid(self.r_values)
        result = np.isclose(_ma, _mb, rtol=rtol, atol=atol)
        if not result.all():
            # return the full array including nans
            return self.l_values - self.r_values
        return None

    def isclose(self, rtol: float, atol: float):
        return np.isclose(self.l_values, self.r_values, atol=atol, rtol=rtol)


class LocationDiff(BaseModel):
    l_value: Union['float', None]
    r_value: Union['float', None]


class LocationMap(BaseModel):
    location_code: str
    map: dict[str, LocationDiff]


class GridDiffDiagnostic(BaseModel):
    """Capture information about grid differences from two grid record sources."""

    atol: float
    rtol: float
    region_grid_id: str
    r_source: str = ""
    l_source: str = ""
    location_map: dict[str, LocationMap]
    checked_grid_entries: int = 0
    failed_grid_entries: int = 0

    @property
    def location_codes(self):
        return [loc.code for loc in get_locations(locations=[self.region_grid_id])]

    def check_diff(self, diff: GridDiff) -> Optional[str]:
        self.checked_grid_entries += 1
        # numeric_diff = diff.numeric_difference(rtol=self.rtol, atol=self.atol)
        # if numeric_diff is not None:
        errors = np.where(diff.isclose(rtol=self.rtol, atol=self.atol) is False)[0].tolist()
        if len(errors):
            self.failed_grid_entries += 1
            # print(errors)
            for idx in errors:
                location = self.location_codes[idx]
                location_diff = LocationDiff(l_value=diff.l_values.tolist()[idx], r_value=diff.r_values.tolist()[idx])
                map_entry = self.location_map.get(location)
                if not map_entry:
                    map_entry = LocationMap(location_code=location, map={})
                    self.location_map[location] = map_entry
                map_entry.map[diff.grid_id.to_idx()] = location_diff
            return f'DIFF :: {diff.grid_id} :: {len(errors)}'
        return None


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

    # print(region_grid_id)
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

        if hits % 100 == 0:
            with open('grid_analysis.wip.json', 'w') as fp:
                json.dump(diagnostic.model_dump(), fp, indent=2)

    with open('grid_analysis.json', 'w') as fp:
        json.dump(diagnostic.model_dump(), fp, indent=2)

    click.echo('DONE')


if __name__ == "__main__":
    main()
