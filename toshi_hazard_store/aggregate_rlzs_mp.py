from dis import dis
import json
import multiprocessing
from operator import inv
import time
from collections import namedtuple
from pathlib import Path


from toshi_hazard_store.aggregate_rlzs import build_rlz_table, get_levels, process_location_list, concat_df_files, get_imts, process_disagg_location_list
from toshi_hazard_store.branch_combinator.branch_combinator import get_weighted_branches
from toshi_hazard_store.branch_combinator.branch_combinator import grouped_ltbs, merge_ltbs, merge_ltbs_fromLT

from toshi_hazard_store.branch_combinator.SLT_TAG_FINAL import logic_tree_permutations
from toshi_hazard_store.branch_combinator.SLT_TAG_FINAL import data as gtdata

# from toshi_hazard_store.branch_combinator.SLT_TAG_TD import logic_tree_permutations
# from toshi_hazard_store.branch_combinator.SLT_TAG_TD import data as gtdata

# from toshi_hazard_store.branch_combinator.SLT_TAG_TI import logic_tree_permutations
# from toshi_hazard_store.branch_combinator.SLT_TAG_TI import data as gtdata



# from toshi_hazard_store.data_functions import weighted_quantile
from toshi_hazard_store.locations import locations_nzpt2_and_nz34_chunked, locations_nz34_chunked, locations_nz2_chunked

class DisaggHardWorker(multiprocessing.Process):
    """A worker that batches and saves records to DynamoDB.

    based on https://pymotw.com/2/multiprocessing/communication.html example 2.
    """

    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self):
        print(f"worker {self.name} running.")
        proc_name = self.name

        while True:
            nt = self.task_queue.get()
            if nt is None:
                # Poison pill means shutdown
                self.task_queue.task_done()
                print('%s: Exiting' % proc_name)
                break

            # tic = time.perf_counter()
            disagg_configs = process_disagg_location_list(
                nt.hazard_curves, nt.source_branches, nt.toshi_ids, nt.poes, nt.inv_time, nt.vs30, nt.locs, nt.aggs, nt.imts
            )
            self.task_queue.task_done()
            self.result_queue.put(disagg_configs)

        return


class AggHardWorker(multiprocessing.Process):
    """A worker that batches and saves records to DynamoDB.

    based on https://pymotw.com/2/multiprocessing/communication.html example 2.
    """

    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self):
        print(f"worker {self.name} running.")
        proc_name = self.name

        while True:
            nt = self.task_queue.get()
            if nt is None:
                # Poison pill means shutdown
                self.task_queue.task_done()
                print('%s: Exiting' % proc_name)
                break

            # tic = time.perf_counter()
            binned_hazard_df = process_location_list(
                nt.locs, nt.toshi_ids, nt.source_branches, nt.aggs, nt.imts, nt.levels, nt.vs30
            )
            df_name = Path(f"df_{nt.grid_loc}_aggregates.json")
            self.task_queue.task_done()
            binned_hazard_df.to_json(df_name)
            print(f"worker {self.name} saved {df_name} for {len(nt.locs)} locations.")
            self.result_queue.put(str(df_name))

        return


AggTaskArgs = namedtuple("AggTaskArgs", "grid_loc locs toshi_ids source_branches aggs imts levels vs30")
DisaggTaskArgs = namedtuple("DisaggTaskArgs", "grid_loc hazard_curves source_branches toshi_ids poes inv_time vs30 locs aggs imts")


def process_agg(vs30, location_generator, aggs, imts=None, output_prefix='', num_workers=12):    
    
    # source_branches = load_source_branches()
    # omit = ['T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTA2MDEy']  # this is the failed/clonded job in first GT_37

    omit = []
    toshi_ids = [b.hazard_solution_id for b in merge_ltbs_fromLT(logic_tree_permutations, gtdata=gtdata, omit=omit)]
    
    grouped = grouped_ltbs(merge_ltbs_fromLT(logic_tree_permutations, gtdata=gtdata, omit=omit))
    source_branches = get_weighted_branches(grouped)

    if not imts:
        imts = get_imts(source_branches, vs30)

    binned_locs = location_generator()
    levels = get_levels(source_branches, list(binned_locs.values())[0], vs30)  # TODO: get seperate levels for every IMT
    
    for i in range(len(source_branches)):
        rlz_combs, weight_combs = build_rlz_table(source_branches[i], vs30)
        source_branches[i]['rlz_combs'] = rlz_combs
        source_branches[i]['weight_combs'] = weight_combs

    ###########
    #
    # MULTIPROC
    #
    ###########
    task_queue: multiprocessing.JoinableQueue = multiprocessing.JoinableQueue()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    print('Creating %d workers' % num_workers)
    workers = [AggHardWorker(task_queue, result_queue) for i in range(num_workers)]
    for w in workers:
        w.start()

    tic = time.perf_counter()
    # Enqueue jobs
    num_jobs = 0
    for key, locs in location_generator().items():
        t = AggTaskArgs(key, locs, toshi_ids, source_branches, aggs, imts, levels, vs30)
        task_queue.put(t)
        num_jobs += 1

    # Add a poison pill for each to signal we've done everything
    for i in range(num_workers):
        task_queue.put(None)

    # Wait for all of the tasks to finish
    task_queue.join()

    # Start printing results
    print('Results:')
    df_file_names = []
    while num_jobs:
        result = result_queue.get()
        df_file_names.append(result)
        print(str(result))
        num_jobs -= 1
    
    toc = time.perf_counter()
    print(f'time to run aggregations: {toc-tic:.0f} seconds')

    file_name = '_'.join( (output_prefix,'all_aggregates.json') )
    hazard_curves = concat_df_files(df_file_names)

    hazard_curves.to_json(file_name)

    return hazard_curves, source_branches

    # hazard_curves = pd.concat([hazard_curves, binned_hazard_curves])
    # print(hazard_curves)


def process_disaggs(hazard_curves, source_branches, poes, inv_time, vs30, location_generator, aggs, imts, num_workers=12):

    # write serial code for now, parallelize once it works 
    omit = []
    toshi_ids = [b.hazard_solution_id for b in merge_ltbs_fromLT(logic_tree_permutations, gtdata=gtdata, omit=omit)]

    task_queue: multiprocessing.JoinableQueue = multiprocessing.JoinableQueue()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    print('Starting Disaggregations')
    print('Creating %d workers' % num_workers)
    workers = [DisaggHardWorker(task_queue, result_queue) for i in range(num_workers)]
    for w in workers:
        w.start()

    tic = time.perf_counter()
    # Enqueue jobs
    num_jobs = 0
    for key, locs in location_generator().items():
        print(locs)
        t = DisaggTaskArgs(key, hazard_curves, source_branches, toshi_ids, poes, inv_time, vs30, locs, aggs, imts)
        task_queue.put(t)
        num_jobs += 1

    # Add a poison pill for each to signal we've done everything
    for i in range(num_workers):
        task_queue.put(None)

    # Wait for all of the tasks to finish
    task_queue.join()

    # Start printing results
    print('Results:')
    disagg_configs = []
    while num_jobs:
        result = result_queue.get()
        disagg_configs += result
        print(str(result))
        num_jobs -= 1
    
    toc = time.perf_counter()
    print(f'time to run disaggregations: {toc-tic:.0f} seconds')

    return disagg_configs


    #========================================#

    # disagg_configs = []
    # for key, locs in location_generator().items():
    #     disagg_configs += process_disagg_location_list(hazard_curves, source_branches, toshi_ids, poes, inv_time, vs30, locs, aggs, imts)

    # return disagg_configs


if __name__ == "__main__":

    nproc = 20

    classical = False

    output_prefix = 'TI_sensivitiy'
    vs30 = 400
    aggs = ['mean', 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 0.8, 0.9, 0.95, 0.975, 0.99, 0.995]
    # imts = ['PGA', 'SA(0.5)', 'SA(1.0)', 'SA(1.5)', 'SA(2.0)', 'SA(3.0)']
    imts = ['PGA', 'SA(0.5)', 'SA(1.5)', 'SA(3.0)']
    # imts = None
    # location_generator = locations_nzpt2_and_nz34_chunked
    location_generator = locations_nz34_chunked
    
    
    if classical:
        hazard_curves, source_branches = process_agg(vs30, location_generator, aggs, imts, output_prefix=output_prefix, num_workers=nproc)

    # if running classical and disagg you must make sure that the requested locations, imts, vs30, aggs for disaggs are in what was requested for the classical calculation
    disaggs = True
    poes = [0.1,0.02]
    aggs = ['mean']
    inv_time = 50
    imts = ['PGA','SA(0.5)','SA(1.5)']
    output_prefix = 'fullLT_dissags'
    location_generator = locations_nz34_chunked
    # location_generator = locations_nz2_chunked
    # breakpoint()

    if disaggs:
        if classical:
            disagg_configs = process_disaggs(hazard_curves, source_branches, vs30, location_generator, aggs, imts, num_workers=nproc)
        else:
            hazard_curves, source_branches = process_agg(vs30, location_generator, aggs, imts, output_prefix='for_disaggs', num_workers=nproc)
            disagg_configs = process_disaggs(hazard_curves, source_branches, poes, inv_time, vs30, location_generator, aggs, imts, num_workers=nproc)

        # add location code for sites that have them
        from nzshm_common.location.location import LOCATIONS_BY_ID
        from nzshm_common.location.code_location import CodedLocation
        for disagg_config in disagg_configs:
            for loc in LOCATIONS_BY_ID.values():
                location = CodedLocation(loc['latitude'],loc['longitude']).downsample(.001).code
                if location == disagg_config['location']:
                    disagg_config['site_code'] = loc['id']
                    disagg_config['site_name'] = loc['name']


        with open('disagg_configs.json','w') as json_file:
            json.dump(disagg_configs,json_file)




