import itertools
import ast
import time

import numpy as np

from operator import mul
from functools import reduce

from toshi_hazard_store.data_functions import weighted_quantile
from toshi_hazard_store.query_v3 import get_rlz_curves_v3, get_hazard_metadata_v3

inv_time = 1.0
VERBOSE = False

def get_imts(source_branches, vs30):

    ids = source_branches[0]['ids']
    meta = next(get_hazard_metadata_v3(ids, [vs30]))
    imts = list(meta.imts)
    imts.sort()

    return imts

def cache_realization_values(source_branches, loc, vs30):

    tic = time.perf_counter()

    values = {}
    for branch in source_branches:
        for res in get_rlz_curves_v3([loc], [vs30], None, branch['ids'], None):
            key = ':'.join((res.hazard_solution_id,str(res.rlz))) 
            values[key] = {}
            for val in res.values:
                values[key][val.imt] = np.array(val.vals)
    
    toc = time.perf_counter()
    if VERBOSE:
        print(f'time to load realizations: {toc-tic:.1f} seconds')

    return values

def build_rlz_table(branch, vs30):

    tic = time.perf_counter()

    ids=branch['ids']
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
                rlz_key = ':'.join((hazard_id,rlz))
                rlz_sets[trt][gsim].append(rlz_key)
                weight_sets[trt][gsim] = gsim_lt['weight'][rlz] # this depends on only one source per run and the same gsim weights in every run

    rlz_sets_tmp = rlz_sets.copy()
    weight_sets_tmp = weight_sets.copy()
    for k,v in rlz_sets.items():
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
    for src_group in rlz_iter: # could be done with list comprehension, but I can't figure out the syntax?
        rlz_combs.append([s for src in src_group for s in src])

    # TODO: I sure hope itertools.product produces the same order every time
    weight_iter = itertools.product(*weight_lists)
    weight_combs = []
    for src_group in weight_iter: # could be done with list comprehension, but I can't figure out the syntax?
        weight_combs.append(reduce(mul, src_group, 1) )

    toc = time.perf_counter()
    if VERBOSE:
        print(f'time to build realization table: {toc-tic:.1f} seconds')

    return rlz_combs, weight_combs


def get_weights(branch, vs30):

    weights = {}
    ids=branch['ids']
    for meta in get_hazard_metadata_v3(ids, [vs30]):
        rlz_lt = ast.literal_eval(meta.rlz_lt) #TODO should I be using this or gsim_lt?
        hazard_id = meta.hazard_solution_id

        for rlz,weight in rlz_lt['weight'].items():
            rlz_key = ':'.join((hazard_id,rlz))
            weights[rlz_key] = weight

    return weights


def prob_to_rate(prob):

    return -np.log(1-prob)/inv_time

def rate_to_prob(rate):

    return 1.0 - np.exp(-inv_time*rate)


def build_source_branch(values, rlz_combs, imt):

    k = next(iter(values.keys()))
    kk = next(iter(values[k].keys()))
    rate_shape = values[k][kk].shape
    tic = time.perf_counter()
    for i,rlz_comb in enumerate(rlz_combs):
        rate = np.zeros(rate_shape)
        for rlz in rlz_comb:
            rate += prob_to_rate(values[rlz][imt])
        prob = rate_to_prob(rate)
        if i==0:
            prob_table = np.array(prob)
        else:
            prob_table = np.vstack((prob_table,np.array(prob)))

    toc = time.perf_counter()
    if VERBOSE:
        print(f'time to build source branch table table: {toc-tic:.1f} seconds')
    
    return prob_table


def build_source_branch_ws(values, rlz_combs, weights):
    '''DEPRECIATED'''

    branch_weights = []
    for i,rlz_comb in enumerate(rlz_combs):
        branch_weight = 1
        rate = np.zeros(next(iter(values.values())).shape)
        for rlz in rlz_comb:
            print(rlz)
            rate += prob_to_rate(values[rlz]) * weights[rlz]
            branch_weight *= weights[rlz]
        
        prob = rate_to_prob(rate)
        print(rate)
        print('-'*50)
        print(prob)
        print('='*50)
        
        if i==0:
            prob_table = np.array(prob)
        else:
            prob_table = np.vstack((prob_table,np.array(prob)))
        branch_weights.append(branch_weight)
    
    return prob_table, branch_weights

def calculate_agg(branch_probs, agg, weight_combs):

    tic = time.perf_counter()
    median = np.array([])
    for i in range(branch_probs.shape[1]):
        quantiles = weighted_quantile(branch_probs[:,i],agg,sample_weight=weight_combs)
        median = np.append(median,np.array(quantiles))
    
    toc = time.perf_counter()
    print(f'time to calulate single aggrigation: {toc-tic:.4f} seconds')

    return median

def build_branches(source_branches, values, imt, vs30):
    '''for each source branch, assemble the gsim realization combinations'''
    
    tic = time.perf_counter()

    weights = np.array([])
    for i,branch in enumerate(source_branches):

        rlz_combs, weight_combs = build_rlz_table(branch, vs30)
        w = np.array(weight_combs) * branch['weight']
        weights = np.hstack( (weights,w) )
                
         #set of realization probabilties for a single complete source branch
         #these can then be aggrigated in prob space (+/- impact of NB) to create a hazard curve
        if i==0:
            branch_probs = build_source_branch(values, rlz_combs, imt) 
        else:
            branch_probs = np.vstack((branch_probs,build_source_branch(values, rlz_combs, imt)))

    toc = time.perf_counter()
    print(f'time to build branches: {toc-tic:.4f} seconds')

    return weights, branch_probs



if __name__ == "__main__":

    tic_total = time.perf_counter()

    # TODO: I'm making assumptions that the levels array is the same for every realization, imt, run, etc. 
    # If that were not the case, I would have to add some interpolation

    # loc = "-41.300~174.780" #WLG
    loc = "-43.530~172.630" #CHC
    vs30 = 750
    agg = 'mean'
    # agg = [0.5]
    
    source_branches = [
        dict(name='A', ids=['A_CRU', 'A_HIK', 'A_PUY'], weight=0.25),
        dict(name='B', ids=['B_CRU', 'B_HIK', 'B_PUY'], weight=0.75),
    ]

    imts = get_imts(source_branches, vs30)

    values = cache_realization_values(source_branches, loc, vs30)

    median = {}
    for imt in imts:
        weights, branch_probs = build_branches(source_branches, values, imt, vs30)
        median[imt] =  calculate_agg(branch_probs, agg, weights) # TODO: could be stored in pandas DataFrame
    
    toc_total = time.perf_counter()
    print(f'total time: {toc_total-tic_total:.1f} seconds')

    for k,v in median.items():
        print('='*50)
        print(f'{k}:')
        print(v[:4],'...',v[-4:])


