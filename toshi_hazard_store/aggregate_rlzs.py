import ast
import csv
import itertools
import time
from functools import reduce
from operator import mul

import numpy as np
import pandas as pd

from toshi_hazard_store.branch_combinator.branch_combinator import get_branches, get_weighted_branches
from toshi_hazard_store.branch_combinator.SLT_37_GRANULAR_RELEASE_1 import logic_tree_permutations
from toshi_hazard_store.branch_combinator.SLT_37_GT import grouped_ltbs, merge_ltbs
from toshi_hazard_store.data_functions import weighted_quantile
from toshi_hazard_store.locations import locations_nzpt2_and_nz34_binned
from toshi_hazard_store.query_v3 import get_hazard_metadata_v3, get_rlz_curves_v3

inv_time = 1.0
VERBOSE = True


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
    print(f'time to load realizations: {toc-tic:.1f} seconds')

    return values


def build_rlz_table(branch, vs30):

    tic = time.perf_counter()

    ids = branch['ids']
    rlz_sets = {}
    weight_sets = {}
    for meta in get_hazard_metadata_v3(ids, [vs30]):
        gsim_lt = ast.literal_eval(meta.gsim_lt)
        trts = list(set(gsim_lt['trt'].values()))
        trts.sort()
        for trt in trts:
            rlz_sets[trt] = {}
            weight_sets[trt] = {}

    for meta in get_hazard_metadata_v3(ids, [vs30]):
        rlz_lt = ast.literal_eval(meta.rlz_lt)
        for trt in rlz_sets.keys():
            if trt in rlz_lt:
                gsims = list(set(rlz_lt[trt].values()))
                gsims.sort()
                for gsim in gsims:
                    rlz_sets[trt][gsim] = []

    for meta in get_hazard_metadata_v3(ids, [vs30]):
        rlz_lt = ast.literal_eval(meta.rlz_lt)
        gsim_lt = ast.literal_eval(meta.gsim_lt)
        hazard_id = meta.hazard_solution_id
        trts = list(set(gsim_lt['trt'].values()))
        trts.sort()
        for trt in trts:
            for rlz, gsim in rlz_lt[trt].items():
                rlz_key = ':'.join((hazard_id, rlz))
                rlz_sets[trt][gsim].append(rlz_key)
                weight_sets[trt][gsim] = gsim_lt['weight'][
                    rlz
                ]  # this depends on only one source per run and the same gsim weights in every run

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
    cnt = 0
    for imt in imts:
        print(f'working on {imt}')
        for loc in locs:
            weights, branch_probs = build_branches(source_branches, values, imt, loc, vs30)
            tic_agg = time.perf_counter()
            hazard = calculate_aggs(branch_probs, aggs, weights)
            for aggind, agg in enumerate(aggs):
                lat, lon = loc.split('~')
                for j, level in enumerate(levels):
                    # breakpoint()
                    binned_hazard_curves.loc[cnt, 'lat':'agg'] = pd.Series(
                        {'lat': lat, 'lon': lon, 'imt': imt, 'agg': str(agg)}
                    )
                    binned_hazard_curves.loc[cnt, 'level':'hazard'] = pd.Series(
                        {'level': level, 'hazard': hazard[j, aggind]}
                    )
                    cnt += 1

            toc_agg = time.perf_counter()
            print(f'time to perform all aggregations for 1 location {loc}: {toc_agg-tic_agg:.4f} seconds')
    return binned_hazard_curves


if __name__ == "__main__":

    tic_total = time.perf_counter()

    # TODO: I'm making assumptions that the levels array is the same for every realization, imt, run, etc.
    # If that were not the case, I would have to add some interpolation

    binned_locs = locations_nzpt2_and_nz34_binned(grid_res=1.0, point_res=0.001)

    vs30 = 750
    aggs = ['mean', 0.05, 0.1, 0.2, 0.5, 0.8, 0.9, 0.95]

    # source_branches = load_source_branches()
    omit = ['T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTA2MDEy']  # this is the failed/clonded job
    toshi_ids = [b.hazard_solution_id for b in merge_ltbs(logic_tree_permutations, omit)]

    grouped_ltbs = grouped_ltbs(merge_ltbs(logic_tree_permutations, omit))
    source_branches = get_weighted_branches(grouped_ltbs)

    # print(source_branches)

    imts = get_imts(source_branches, vs30)
    levels = get_levels(source_branches, list(binned_locs.values())[0], vs30)  # TODO: get seperate levels for every IMT

    columns = ['lat', 'lon', 'imt', 'agg', 'level', 'hazard']
    # index = range(len(locs)*len(imts)*len(aggs)*len(levels))
    hazard_curves = pd.DataFrame(columns=columns)

    for i in range(len(source_branches)):
        rlz_combs, weight_combs = build_rlz_table(source_branches[i], vs30)
        source_branches[i]['rlz_combs'] = rlz_combs
        source_branches[i]['weight_combs'] = weight_combs

    for key, locs in locations_nzpt2_and_nz34_binned(grid_res=1.0, point_res=0.001).items():
        binned_hazard_curves = process_location_list(locs[:1], toshi_ids, source_branches, aggs, vs30)
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
