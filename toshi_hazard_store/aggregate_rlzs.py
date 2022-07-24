import ast
import csv
from dis import dis
from heapq import merge
import itertools
import time
import math
from functools import reduce
from operator import inv, mul

import numpy as np
import pandas as pd

from toshi_hazard_store.branch_combinator.branch_combinator import get_branches, get_weighted_branches
from toshi_hazard_store.branch_combinator.SLT_37_GRANULAR_RELEASE_1 import logic_tree_permutations
from toshi_hazard_store.branch_combinator.branch_combinator import grouped_ltbs, merge_ltbs, merge_ltbs_fromLT
from toshi_hazard_store.data_functions import weighted_quantile
from toshi_hazard_store.locations import locations_nzpt2_and_nz34_binned, just_akl
from toshi_hazard_store.query_v3 import get_hazard_metadata_v3, get_rlz_curves_v3

# from toshi_hazard_store.branch_combinator.SLT_TAG_FINAL import logic_tree_permutations
# from toshi_hazard_store.branch_combinator.SLT_TAG_FINAL import data as gtdata

# from toshi_hazard_store.branch_combinator.SLT_TAG_TI import logic_tree_permutations
# from toshi_hazard_store.branch_combinator.SLT_TAG_TI import data as gtdata

from toshi_hazard_store.branch_combinator.SLT_NBsens_1 import logic_tree_permutations
from toshi_hazard_store.branch_combinator.SLT_NBsens_1 import data as gtdata


from toshi_hazard_store.locations import locations_nzpt2_and_nz34_chunked

inv_time = 1.0
VERBOSE = False


def get_imts(source_branches, vs30):

    ids = source_branches[0]['ids']
    meta = next(get_hazard_metadata_v3(ids, [vs30]))
    imts = list(meta.imts)
    imts.sort()

    return imts


def load_realization_values(toshi_ids, locs, vs30s):

    tic = time.perf_counter()
    # unique_ids = []
    # for branch in source_branches:
    #     unique_ids += branch['ids']
    # unique_ids = list(set(unique_ids))
    print(f'loading {len(toshi_ids)} hazard IDs . . . ')

    values = {}
    for res in get_rlz_curves_v3(locs, vs30s, None, toshi_ids, None):
        key = ':'.join((res.hazard_solution_id, str(res.rlz)))
        if key not in values:
            values[key] = {}
        values[key][res.nloc_001] = {}
        for val in res.values:
            values[key][res.nloc_001][val.imt] = np.array(val.vals)

    # check that the correct number of records came back
    ids_ret = []
    for k1, v1 in values.items():
        nlocs_ret = len(v1.keys())
        if not nlocs_ret == len(locs):
            print(f'!!!!!!!!! {k1} missing {len(locs) - nlocs_ret} locations')
        ids_ret += [k1.split(':')[0]]
    ids_ret = set(ids_ret)
    if len(ids_ret) != len(toshi_ids):
        print(f'!!!!!!!!! missing {len(toshi_ids)-len(ids_ret)} IDs')
        toshi_ids = set(toshi_ids)
        print(f'!!!!!!!!! missing {toshi_ids - ids_ret}')

    toc = time.perf_counter()
    # print(f'time to load realizations: {toc-tic:.1f} seconds')

    return values


def get_trts(gsim_lt, merged_trt):
    trts = list(set(gsim_lt['trt'].values()))
    trts.sort()
    return trts


def build_rlz_table(branch, vs30, merge_trts=[]):

    #TODO: trim 'Slab' and 'Inter' off gsim names, this is not very generalized

    div = '+++'
    merged_trt = div.join(merge_trts)

    tic = time.perf_counter()
    
    ids = branch['ids']
    rlz_sets = {}
    weight_sets = {}
    for meta in get_hazard_metadata_v3(ids, [vs30]):
        gsim_lt = ast.literal_eval(meta.gsim_lt)
        trts = get_trts(gsim_lt, merged_trt)
        for trt in trts:
            mtrt = merged_trt if trt in merged_trt else trt
            rlz_sets[mtrt] = {}
            weight_sets[mtrt] = {}

    for meta in get_hazard_metadata_v3(ids, [vs30]):
        rlz_lt = ast.literal_eval(meta.rlz_lt)
        for mtrt in rlz_sets.keys():
            for trt in mtrt.split(div):
                if trt in rlz_lt:
                    gsims = list(set(rlz_lt[trt].values()))
                    gsims.sort()
                    for gsim in gsims:
                        rlz_sets[mtrt][gsim] = []

    for meta in get_hazard_metadata_v3(ids, [vs30]):
        rlz_lt = ast.literal_eval(meta.rlz_lt)
        gsim_lt = ast.literal_eval(meta.gsim_lt)
        hazard_id = meta.hazard_solution_id
        trts = get_trts(gsim_lt, merged_trt)
        for trt in trts:
            mtrt = merged_trt if trt in merged_trt else trt
            for rlz, gsim in rlz_lt[trt].items():
                rlz_key = ':'.join((hazard_id, rlz))
                rlz_sets[mtrt][gsim].append(rlz_key)
                weight_sets[mtrt][gsim] = gsim_lt['weight'][
                    rlz
                ]  # this depends on only one source per run and the same gsim weights in every run

    breakpoint()
  
    rlz_sets_tmp = rlz_sets.copy()
    weight_sets_tmp = weight_sets.copy()
    for k, v in rlz_sets.items():
        rlz_sets_tmp[k] = []
        weight_sets_tmp[k] = []
        for gsim in v.keys():
            rlz_sets_tmp[k].append(v[gsim])
            weight_sets_tmp[k].append(weight_sets[k][gsim])

    rlz_lists = list(rlz_sets_tmp.values())
    weight_lists = list(weight_sets_tmp.values())

    # TODO: fix rlz from the same ID grouped together

    rlz_iter = itertools.product(*rlz_lists)
    rlz_combs = []
    for src_group in rlz_iter:  # could be done with list comprehension, but I can't figure out the syntax?
        rlz_combs.append([s for src in src_group for s in src])

    # TODO: I sure hope itertools.product produces the same order every time
    weight_iter = itertools.product(*weight_lists)
    weight_combs = []
    for src_group in weight_iter:  # could be done with list comprehension, but I can't figure out the syntax?
        weight_combs.append(reduce(mul, src_group, 1))

    toc = time.perf_counter()
    if VERBOSE:
        print(f'time to build realization table: {toc-tic:.1f} seconds')

    return rlz_combs, weight_combs


def get_weights(branch, vs30):

    weights = {}
    ids = branch['ids']
    for meta in get_hazard_metadata_v3(ids, [vs30]):
        rlz_lt = ast.literal_eval(meta.rlz_lt)  # TODO should I be using this or gsim_lt?
        hazard_id = meta.hazard_solution_id

        for rlz, weight in rlz_lt['weight'].items():
            rlz_key = ':'.join((hazard_id, rlz))
            weights[rlz_key] = weight

    return weights


def prob_to_rate(prob):

    return -np.log(1 - prob) / inv_time


def rate_to_prob(rate):

    return 1.0 - np.exp(-inv_time * rate)


def build_source_branch(values, rlz_combs, imt, loc):

    # TODO: there has got to be a better way to do this!
    k1 = next(iter(values.keys()))
    k2 = next(iter(values[k1].keys()))
    k3 = next(iter(values[k1][k2].keys()))
    rate_shape = values[k1][k2][k3].shape

    tic = time.perf_counter()
    for i, rlz_comb in enumerate(rlz_combs):
        rate = np.zeros(rate_shape)
        for rlz in rlz_comb:
            rate += prob_to_rate(values[rlz][loc][imt])
        prob = rate_to_prob(rate)
        if i == 0:
            prob_table = np.array(prob)
        else:
            prob_table = np.vstack((prob_table, np.array(prob)))

    toc = time.perf_counter()
    # if VERBOSE:
    #     print(f'time to build source branch table: {toc-tic:.1f} seconds')

    return prob_table


def build_source_branch_ws(values, rlz_combs, weights):
    '''DEPRECIATED'''

    branch_weights = []
    for i, rlz_comb in enumerate(rlz_combs):
        branch_weight = 1
        rate = np.zeros(next(iter(values.values())).shape)
        for rlz in rlz_comb:
            print(rlz)
            rate += prob_to_rate(values[rlz]) * weights[rlz]
            branch_weight *= weights[rlz]

        prob = rate_to_prob(rate)
        print(rate)
        print('-' * 50)
        print(prob)
        print('=' * 50)

        if i == 0:
            prob_table = np.array(prob)
        else:
            prob_table = np.vstack((prob_table, np.array(prob)))
        branch_weights.append(branch_weight)

    return prob_table, branch_weights


def calculate_aggs(branch_probs, aggs, weight_combs):

    tic = time.perf_counter()
    median = np.array([])
    for i in range(branch_probs.shape[1]):
        quantiles = weighted_quantile(branch_probs[:, i], aggs, sample_weight=weight_combs)
        if i == 0:
            median = np.array(quantiles)
        else:
            median = np.vstack((median, quantiles))
    toc = time.perf_counter()
    # if VERBOSE:
    #     print(f'time to calulate single aggrigation: {toc-tic:.4f} seconds')

    return median


def build_branches(source_branches, values, imt, loc, vs30):
    '''for each source branch, assemble the gsim realization combinations'''

    tic = time.perf_counter()

    weights = np.array([])
    for i, branch in enumerate(source_branches):

        # rlz_combs, weight_combs = build_rlz_table(branch, vs30)
        rlz_combs = branch['rlz_combs']
        weight_combs = branch['weight_combs']

        w = np.array(weight_combs) * branch['weight']
        weights = np.hstack((weights, w))

        # set of realization probabilties for a single complete source branch
        # these can then be aggrigated in prob space (+/- impact of NB) to create a hazard curve
        if i == 0:
            branch_probs = build_source_branch(values, rlz_combs, imt, loc)
        else:
            branch_probs = np.vstack((branch_probs, build_source_branch(values, rlz_combs, imt, loc)))

    toc = time.perf_counter()
    if VERBOSE:
        print(f'time to build branches: {toc-tic:.4f} seconds')

    return weights, branch_probs


def read_locs():
    '''DEPRECIATED'''

    csv_file_path = '/home/chrisdc/NSHM/DEV/toshi-hazard-store/data/hazard_curve-mean-PGA_35.csv'
    with open(csv_file_path) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        header = next(reader)
        header = next(reader)
        location_codes = []
        for row in reader:
            lon = float(row[1])
            lat = float(row[2])
            location_codes.append(f'{lat:0.3f}~{lon:0.3f}')

    return location_codes


def load_source_branches():

    source_branches = [
        dict(name='test', ids=['T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTA2MDE0', 'A'], weight=1.0)
        # dict(name='A', ids=['A_CRU', 'A_HIK', 'A_PUY'], weight=0.25),
        # dict(name='B', ids=['B_CRU', 'B_HIK', 'B_PUY'], weight=0.75),
    ]

    return source_branches


def get_levels(source_branches, locs, vs30):

    id = source_branches[0]['ids'][0]

    hazard = next(get_rlz_curves_v3([locs[0]], [vs30], None, [id], None))

    return hazard.values[0].lvls


# process_location_list(locs, toshi_ids, source_branches, aggs, imts, levels, vs30)
def process_location_list(locs, toshi_ids, source_branches, aggs, imts, levels, vs30):
    print(f'get values for {len(locs)} locations and {len(toshi_ids)} hazard_solutions')
    values = load_realization_values(toshi_ids, locs, [vs30])

    tic = time.perf_counter()
    columns = ['lat', 'lon', 'imt', 'agg', 'level', 'hazard']
    index = range(len(locs) * len(imts) * len(aggs) * len(levels))
    binned_hazard_curves = pd.DataFrame(columns=columns, index=index)

    nlocs = len(locs)
    naggs = len(aggs)
    nlevels = len(levels)

    cnt = 0
    start_imt = 0
    for imt in imts:
        print(f'working on {imt}')
        start_loc = start_imt
        stop_imt = start_imt + nlocs * naggs * nlevels
        binned_hazard_curves.loc[start_imt:stop_imt, 'imt'] = imt
        start_imt = stop_imt
        
        for loc in locs:
            lat, lon = loc.split('~')
            start_agg = start_loc
            stop_loc = start_loc + naggs * nlevels
            binned_hazard_curves.loc[start_loc:stop_loc, 'lat'] = lat
            binned_hazard_curves.loc[start_loc:stop_loc, 'lon'] = lon
            start_loc = stop_loc

            weights, branch_probs = build_branches(source_branches, values, imt, loc, vs30)

            tic_agg = time.perf_counter()
            hazard = calculate_aggs(branch_probs, aggs, weights)
            for aggind, agg in enumerate(aggs):

                stop_agg = start_agg + nlevels
                binned_hazard_curves.loc[start_agg:stop_agg, 'agg'] = str(agg)
                start_agg = stop_agg

                # tic = time.perf_counter()
                for j, level in enumerate(levels):

                    # binned_hazard_curves.loc[cnt, 'lat':'agg'] = pd.Series(
                    #     {'lat': lat, 'lon': lon, 'imt': imt, 'agg': str(agg)}
                    # )
                    binned_hazard_curves.loc[cnt, 'level':'hazard'] = pd.Series(
                        {'level': level, 'hazard': hazard[j, aggind]}
                    )
                    cnt += 1
                # toc = time.perf_counter()
                # print(f'time to store in df {toc-tic} seconds')

            toc_agg = time.perf_counter()
            if VERBOSE:
                print(f'time to perform all aggregations for 1 location {loc}: {toc_agg-tic_agg:.4f} seconds')
    
    return binned_hazard_curves

def concat_df_files(df_file_names):
    columns = ['lat', 'lon', 'imt', 'agg', 'level', 'hazard']
    
    hazard_curves = pd.DataFrame(columns=columns)

    dtype = {'lat':str,'lon':str}

    for df_file_name in df_file_names:
        binned_hazard_curves = pd.read_json(df_file_name,dtype=dtype)
        hazard_curves = pd.concat([hazard_curves, binned_hazard_curves],ignore_index=True)
    
    return hazard_curves

def compute_hazard_at_poe(levels,values,poe,inv_time):

    rp = -inv_time/np.log(1-poe)
    haz = np.exp( np.interp( np.log(1/rp), np.flip(np.log(values)), np.flip(np.log(levels)) ) )
    return haz




def process_disagg_location_list(hazard_curves, source_branches, toshi_ids, poes, inv_time, vs30, locs, aggs, imts):    
    

    values = load_realization_values(toshi_ids, locs, [vs30])
    k1 = next(iter(values.keys()))
    k2 = next(iter(values[k1].keys()))
    k3 = next(iter(values[k1][k2].keys()))
    rate_shape = values[k1][k2][k3].shape

    disagg_rlzs = []
    for loc in locs:
        lat, lon = loc.split('~')
        for poe in poes:
            for agg in aggs:
                for imt in imts:
                    disagg_key = ':'.join( (loc,str(poe),str(agg),imt) )
                    

                    # get target level of shaking
                    hc = hazard_curves.loc[(hazard_curves['agg'] == agg) & \
                                            (hazard_curves['imt'] == imt) & \
                                            (hazard_curves['lat'] == lat) & \
                                            (hazard_curves['lon'] == lon)]
                    levels = hc['level'].to_numpy()
                    hazard_vals = hc['hazard'].to_numpy()
                    target_level = compute_hazard_at_poe(levels,hazard_vals,poe,inv_time)
                    min_dist = math.inf

                    # find realization with nearest level of shaking
                    # TODO: repeating a lot of code here. Unify with agg processing code when done
                    for i, branch in enumerate(source_branches):
                        rlz_combs = branch['rlz_combs']

                        for i, rlz_comb in enumerate(rlz_combs):
                            rate = np.zeros(rate_shape)
                            for rlz in rlz_comb:
                                rate += prob_to_rate(values[rlz][loc][imt])
                            prob = rate_to_prob(rate)
                            rlz_level = compute_hazard_at_poe(levels,prob,poe,inv_time)
                            dist = abs(rlz_level - target_level)
                            if dist < min_dist:
                                nearest_rlz = rlz_comb
                                min_dist = dist
                                nearest_level = rlz_level

                    hazard_ids = [id.split(':')[0] for id in nearest_rlz]
                    source_ids, gsims = get_source_and_gsim(nearest_rlz, vs30)
                    
                    disagg_rlzs.append( dict( 
                                            vs30 = vs30,
                                            source_ids=source_ids,
                                            inv_time=inv_time,
                                            imt=imt,
                                            agg=agg,
                                            poe=poe,
                                            level=nearest_level,
                                            location=loc,
                                            gsims=gsims,
                                            dist=min_dist,
                                            nearest_rlz=nearest_rlz,
                                            target_level=target_level,
                                            hazard_ids=hazard_ids
                                            )
                                        )
    return disagg_rlzs


def get_source_and_gsim(rlz, vs30):

    gsims = {}
    source_ids = []
    for rlz_key in rlz:
        id, gsim_rlz = rlz_key.split(':')
        meta = next(get_hazard_metadata_v3([id], [vs30]))
        gsim_lt = ast.literal_eval(meta.gsim_lt)
        rlz_lt = ast.literal_eval(meta.rlz_lt)
        trt = gsim_lt['trt']['0']
        if gsims.get(trt):
            if not gsims[trt] == rlz_lt[trt][gsim_rlz]:
                raise Exception(f'single branch has more than one gsim for trt {trt}')
        gsims[trt] = rlz_lt[trt][gsim_rlz]
        source_ids += (rlz_lt['source combination'][gsim_rlz]).split('|')

    source_ids = [sid for sid in source_ids if sid] #remove empty strings

    return source_ids, gsims





if __name__ == "__main__":

    tic_total = time.perf_counter()

    # TODO: I'm making assumptions that the levels array is the same for every realization, imt, run, etc.
    # If that were not the case, I would have to add some interpolation

    vs30 = 400
    aggs = ['mean', 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 0.8, 0.9, 0.95, 0.975, 0.99]

    binned_locs = just_akl()
    
    omit = []
    toshi_ids = [b.hazard_solution_id for b in merge_ltbs_fromLT(logic_tree_permutations, gtdata=gtdata, omit=omit)]

    
    grouped = grouped_ltbs(merge_ltbs_fromLT(logic_tree_permutations, gtdata=gtdata, omit=omit))
    source_branches = get_weighted_branches(grouped)

    imts = ['PGA']
    # imts = get_imts(source_branches, vs30)
    levels = get_levels(source_branches, list(binned_locs.values())[0], vs30)  # TODO: get seperate levels for every IMT

    columns = ['lat', 'lon', 'imt', 'agg', 'level', 'hazard']
    hazard_curves = pd.DataFrame(columns=columns)

    merge_trts = ['Subduction Interface', 'Subduction Intraslab']
    tic = time.perf_counter()
    for i in range(len(source_branches)):
        rlz_combs, weight_combs = build_rlz_table(source_branches[i], vs30, merge_trts=merge_trts)
        source_branches[i]['rlz_combs'] = rlz_combs
        source_branches[i]['weight_combs'] = weight_combs
    toc = time.perf_counter()
    print(f'time to build all realization tables {toc-tic:.1f} seconds')
    

    for key, locs in just_akl().items():
        binned_hazard_curves = process_location_list(locs, toshi_ids, source_branches, aggs, imts, levels, vs30)
        binned_hazard_curves.to_json(f"./df_{key}_aggregates.json")
        hazard_curves = pd.concat([hazard_curves, binned_hazard_curves])

    toc = time.perf_counter()
    print(f'agg time: {toc-tic:.1f} seconds')
    print(f'total imts: {len(imts)}')
    print(f'total locations: {len(locs)}')
    print(f'total aggregations: {len(aggs)}')
    print(f'total levels: {len(levels)}')
    print(f'total time: {toc-tic_total:.1f} seconds')

    print(hazard_curves)
