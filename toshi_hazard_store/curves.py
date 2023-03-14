import pandas as pd
from zipfile import ZIP_BZIP2, ZipFile
from pandas import DataFrame
from pathlib import Path
import math
from typing import List, Any
import os
from collections import namedtuple
from itertools import product
from toshi_hazard_store.query import get_hazard_curves

from nzshm_common.location.location import LOCATIONS_BY_ID
from nzshm_common.grids import RegionGrid
from nzshm_common.location import CodedLocation

ARCHIVE_DIR = Path(os.environ['HAZARD_CURVE_ARCHIVE'])
assert ARCHIVE_DIR.exists()
DTYPE = {'lat':'str', 'lon':'str', 'imt':'str', 'agg':'str', 'level':'float64', 'apoe':'float64'}
SITE_LIST = 'NZ_0_1_NB_1_1'
COLUMNS = ['lat', 'lon', 'imt', 'agg', 'level', 'apoe']
RESOLUTION = 0.001

RecordIdentifier = namedtuple('RecordIdentifier', 'location imt agg')


def all_locations() -> List[CodedLocation]:
    """all locations in NZ35 and 0.1 deg grid"""

    locations_nz35 = [
        CodedLocation( loc['latitude'], loc['longitude'], RESOLUTION)
        for loc in LOCATIONS_BY_ID.values()
    ]

    grid = RegionGrid[SITE_LIST]
    grid_locs = grid.load()
    locations_grid = [
        CodedLocation( *loc, RESOLUTION)
        for loc in grid_locs
    ]
    return locations_nz35 + locations_grid


def archive_filepath(hazard_id: str, vs30: int) -> Path:
    return Path(ARCHIVE_DIR, f'{hazard_id}-{vs30}.bz2')

def empty_hazard() -> DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def load_hazard_curves(hazard_id: str, vs30: int) -> DataFrame:
    """Load hazard curves DataFrame from an archive"""

    if archive_filepath(hazard_id, vs30).exists():
        return pd.read_json(archive_filepath(hazard_id, vs30), dtype=DTYPE)
    else:
        return empty_hazard()


def download_hazard(
        hazard_id: str,
        vs30: int,
        locs: List[CodedLocation],
        imts: List[str],
        aggs: List[str],
) -> DataFrame:
    """download all locations, imts and aggs for a particular hazard_id and vs30."""

    loc_strs = [loc.downsample(RESOLUTION).code for loc in locs]
    hazards = get_hazard_curves(
        hazard_model_ids=[hazard_id],
        vs30s = [vs30],
        locs = loc_strs[:1],
        imts = imts,
        aggs = aggs,
    )
    res = next(hazards)
    
    nlevels = len(res.values)
    naggs = len(aggs)
    nimts = len(imts)

    index = range(len(locs) * nimts * naggs * nlevels)
    # hazard_curves = pd.DataFrame(columns=COLUMNS, index=index, dtype=DTYPE)
    hazard_curves = pd.DataFrame({c: pd.Series(dtype=t) for c, t in DTYPE.items()})
    ind = 0
    total_records = len(locs) * len(imts) * len(aggs)
    print(f'retrieving {total_records} records from THS')
    print_step = math.ceil(total_records / 10) 
    for i,res in enumerate(get_hazard_curves(loc_strs, [vs30], [hazard_id], imts, aggs)):
        print(f'retrieved {i / total_records * 100:.0f}% of records from THS') if i%print_step == 0 else None
        lat = f'{res.lat:0.3f}'
        lon = f'{res.lon:0.3f}'
        for value in res.values:
            hazard_curves.loc[ind,'lat'] = lat
            hazard_curves.loc[ind,'lon'] = lon
            hazard_curves.loc[ind,'imt'] = res.imt
            hazard_curves.loc[ind,'agg'] = res.agg
            hazard_curves.loc[ind,'level'] = value.lvl
            hazard_curves.loc[ind,'apoe'] = value.val
            ind += 1

    return hazard_curves


def concat_hazard_curves(hc1: DataFrame, hc2: DataFrame) -> DataFrame:
    return pd.concat((hc1, hc2), ignore_index=True)\
            .drop_duplicates(subset=['lat','lon','imt','agg','level']) 


def save_hazard_curves(hazard_id: str, vs30: int, hazard_curves: DataFrame, append: bool = True) -> DataFrame:

    if archive_filepath(hazard_id, vs30).exists() and append:
        hazard_curves_orig = load_hazard_curves(hazard_id, vs30)
        hazard_curves = concat_hazard_curves(hazard_curves_orig, hazard_curves)

    print('saving hazard curves to archive')
    hazard_curves.to_json(archive_filepath(hazard_id, vs30))
    return hazard_curves


def hazard_from_archive(
        hazard_id: str,
        vs30: int,
        locations: List[CodedLocation],
        imts: List[str],
        aggs: List[str]
) -> DataFrame:
    """open the DataFrame archive and pull out the requested data"""

    lats = [loc.code.split('~')[0] for loc in locations]
    lons = [loc.code.split('~')[1] for loc in locations]

    hdf = load_hazard_curves(hazard_id, vs30)
    hdf = hdf.loc[hdf['lat'].isin(lats)]
    hdf = hdf.loc[hdf['lon'].isin(lons)]
    hdf = hdf.loc[hdf['agg'].isin(aggs)]
    hdf = hdf.loc[hdf['imt'].isin(imts)]

    return hdf
            

def get_hazard(
        hazard_id: str,
        locs: List[CodedLocation],
        vs30: int,
        imts: List[str],
        aggs: List[str],
        no_archive: Any = False
) -> DataFrame:

    if no_archive:
        return download_hazard(hazard_id, vs30, locs, imts, aggs)
    else:
        print('loading hazard curves from archive')
        hazard_curves_arc = load_hazard_curves(hazard_id, vs30)
        locations_arch = [
            CodedLocation(float(lat), float(lon), RESOLUTION)
            for lat, lon in zip(hazard_curves_arc['lat'], hazard_curves_arc['lon'])
        ]
        aggs_arch = list(hazard_curves_arc['agg'])
        imts_arch = list(hazard_curves_arc['imt'])
        records_arch = {RecordIdentifier(loc, imt, agg) for loc, imt, agg in zip(locations_arch, imts_arch, aggs_arch)}
        records_requested = {RecordIdentifier(loc, imt, agg) for loc, imt, agg in product(locs, imts, aggs)}
        records_missing = records_requested - records_arch

        if records_missing:
            locs_request = list({record.location for record in records_missing})
            imts_request = list({record.imt for record in records_missing})
            aggs_request = list({record.agg for record in records_missing})
            hazard_curves = download_hazard(hazard_id, vs30, locs_request, imts_request, aggs_request)
            return save_hazard_curves(hazard_id, vs30, hazard_curves)
        return hazard_curves_arc


def fix_archive(hazard_id, vs30):
    """convert column name from 'hazard' to 'apoe'"""

    hazard = load_hazard_curves(hazard_id, vs30)
    save_hazard_curves(hazard_id, vs30, hazard.rename(columns={'hazard':'apoe'}), append=False)


if __name__ == "__main__":

    hazard_ids = [
        "NSHM_v1.0.1_CRUsens_baseline",
        "NSHM_v1.0.1_sens_jump5km",
        "NSHM_v1.0.1_sens_jump10km",
        "NSHM_v1.0.1_sens_jump10km_iso",
        "NSHM_v1.0.1_sens_jump5km_iso",
        "NSHM_v1.0.1_CRUsens_baseline_iso",
    ]
    hazard_ids = hazard_ids[1:]

    keep = ['WLG','AKL','CHC']
    locations = [CodedLocation(loc['latitude'], loc['longitude'], RESOLUTION) for loc in LOCATIONS_BY_ID.values() if loc['id'] in keep]
    for id in hazard_ids:
        print(f'working on {id}')
        # hazard_curves = get_hazard(id, locations, 400, ['PGA', 'SA(0.5)' ], ['mean'])
        imts = ['PGA', 'SA(0.1)', 'SA(0.2)', 'SA(0.3)', 'SA(0.4)', 'SA(0.5)', 'SA(0.7)','SA(1.0)', 'SA(1.5)', 'SA(2.0)', 'SA(3.0)', 'SA(4.0)', 'SA(5.0)', 'SA(6.0)','SA(7.5)','SA(10.0)']
        aggs = ["mean", "cov", "std", "0.005", "0.01", "0.025", "0.05", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "0.95", "0.975", "0.99", "0.995"]
        download_hazard(id, 400, all_locations(), imts, aggs)