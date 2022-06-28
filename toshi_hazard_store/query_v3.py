"""Queries for saving and retrieving openquake hazard results with convenience."""
from typing import Iterable, Iterator

import toshi_hazard_store.model as model
from toshi_hazard_store.utils import CodedLocation

mOQM = model.ToshiOpenquakeMeta
mRLZ = model.OpenquakeRealization


def get_hazard_metadata_v3(
    haz_sol_ids: Iterable[str] = None,
    vs30_vals: Iterable[int] = None,
) -> Iterator[mOQM]:
    """Fetch ToshiOpenquakeHazardMeta based on criteria."""

    condition_expr = None
    if haz_sol_ids:
        condition_expr = condition_expr & mOQM.hazard_solution_id.is_in(*haz_sol_ids)
    if vs30_vals:
        condition_expr = condition_expr & mOQM.vs30.is_in(*vs30_vals)

    for hit in mOQM.query(
        "ToshiOpenquakeMeta", filter_condition=condition_expr  # NB the partition key is the table name!
    ):
        yield (hit)


def downsample_code(loc_code, res):
    lt = loc_code.split('~')
    assert len(lt) == 2
    return CodedLocation(lat=float(lt[0]), lon=float(lt[1])).downsample(res).code


def get_rlz_curves_v3(
    locs: Iterable[str] = [],  # nloc_001
    vs30s: Iterable[int] = [],  # vs30s
    rlzs: Iterable[int] = [],  # rlzs
    tids: Iterable[str] = [],  # toshi hazard_solution_ids
    imts: Iterable[str] = [],
) -> Iterator[mRLZ]:

    """f'{nloc_001}:{vs30s}:{rlzs}:{self.hazard_solution_id}''

    Use mRLZ.loc_agg_rk range key as much as possible."""

    sort_key_first_val = ""
    condition_expr = None

    # if imts:
    #     first_imt = sorted(imts)[0]
    #     sort_key_first_val += f"{first_imt}"
    #     condition_expr = condition_expr & mOHCR.imt.is_in(*imts)
    if locs:
        # condition_expr = condition_expr & mRLZ.loc.is_in(*locs)
        # condition_expr = condition_expr & mRLZ.sort_key.startswith(locs[0])
        pass  # nee to add nloc fields
    if vs30s:
        condition_expr = condition_expr & mRLZ.vs30.is_in(*vs30s)
    if rlzs:
        condition_expr = condition_expr & mRLZ.rlz.is_in(*rlzs)
    if tids:
        condition_expr = condition_expr & mRLZ.hazard_solution_id.is_in(*tids)

    if locs:
        first_loc = downsample_code(sorted(locs)[0], 0.001)  # these need to be formatted to match the sort key 0.001 ?
        sort_key_first_val += f"{first_loc}"
    if locs and vs30s:
        first_vs30 = sorted(vs30s)[0]
        sort_key_first_val += f":{first_vs30}"
    if locs and vs30s and rlzs:
        first_rlz = sorted(rlzs)[0]
        sort_key_first_val += f":{first_rlz}"
    if locs and vs30s and rlzs and tids:
        first_tid = sorted(tids)[0]
        sort_key_first_val += f":{first_tid}"

    def get_hashes(locs):
        hashes = set()
        for loc in locs:
            lt = loc.split('~')
            assert len(lt) == 2
            hashes.add(downsample_code(loc, 0.1))
        return list(hashes)

    print('hashes', get_hashes(locs))

    for hash_location_code in get_hashes(locs):

        print(f'hash_key {hash_location_code}')
        print(f'sort_key_first_val: {sort_key_first_val}')
        print(f'condition_expr: {condition_expr}')

        if sort_key_first_val:
            qry = mRLZ.query(hash_location_code, mRLZ.sort_key >= sort_key_first_val, filter_condition=condition_expr)
        else:
            qry = mRLZ.query(
                hash_location_code,
                mRLZ.sort_key >= " ",  # lowest printable char in ascii table is SPACE. (NULL is first control)
                filter_condition=condition_expr,
            )

        print(f"get_hazard_rlz_curves_v3: qry {qry}")
        for hit in qry:
            if imts:
                hit.values = list(filter(lambda x: x.imt in imts, hit.values))
            yield (hit)
