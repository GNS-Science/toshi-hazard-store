import logging
import multiprocessing
import time
from collections import namedtuple
from pathlib import Path

from toshi_hazard_store.aggregate_rlzs import (
    build_rlz_table,
    concat_df_files,
    get_imts,
    get_levels,
    process_location_list,
)
from toshi_hazard_store.branch_combinator.branch_combinator import (
    get_weighted_branches,
    grouped_ltbs,
    merge_ltbs_fromLT,
)
from toshi_hazard_store.branch_combinator.SLT_TAG_FINAL import data as gtdata
from toshi_hazard_store.branch_combinator.SLT_TAG_FINAL import logic_tree_permutations

# from toshi_hazard_store.data_functions import weighted_quantile
from toshi_hazard_store.locations import locations_nzpt2_chunked


class AggregationWorkerMP(multiprocessing.Process):
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


def build_source_branches(logic_tree_permutations, gtdata, vs30, omit, truncate=None):

    grouped = grouped_ltbs(merge_ltbs_fromLT(logic_tree_permutations, gtdata=gtdata, omit=omit))
    source_branches = get_weighted_branches(grouped)

    if truncate:
        # for testing only
        source_branches = source_branches[:truncate]

    for i in range(len(source_branches)):
        rlz_combs, weight_combs = build_rlz_table(source_branches[i], vs30)
        source_branches[i]['rlz_combs'] = rlz_combs
        source_branches[i]['weight_combs'] = weight_combs

    return source_branches


def process_agg(vs30, location_generator, aggs, imts=None, output_prefix='', num_workers=12, location_range=None):

    # source_branches = load_source_branches()
    # omit = ['T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTA2MDEy']  # this is the failed/clonded job in first GT_37

    omit = []
    toshi_ids = [b.hazard_solution_id for b in merge_ltbs_fromLT(logic_tree_permutations, gtdata=gtdata, omit=omit)]

    source_branches = build_source_branches(logic_tree_permutations, gtdata, vs30, omit, 2)

    if not imts:
        imts = get_imts(source_branches, vs30)

    binned_locs = location_generator(range=location_range)
    levels = get_levels(source_branches, list(binned_locs.values())[0], vs30)  # TODO: get seperate levels for every IMT

    ###########
    #
    # MULTIPROC
    #
    ###########
    task_queue: multiprocessing.JoinableQueue = multiprocessing.JoinableQueue()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    print('Creating %d workers' % num_workers)
    workers = [AggregationWorkerMP(task_queue, result_queue) for i in range(num_workers)]
    for w in workers:
        w.start()

    tic = time.perf_counter()
    # Enqueue jobs
    num_jobs = 0
    for key, locs in location_generator(range=location_range).items():
        t = AggTaskArgs(key, locs, toshi_ids, source_branches, aggs, imts, levels, vs30)
        task_queue.put(t)
        num_jobs += 1
        break

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
        break

    toc = time.perf_counter()
    print(f'time to run aggregations: {toc-tic:.0f} seconds')

    file_name = '_'.join((output_prefix, 'all_aggregates.json'))
    hazard_curves = concat_df_files(df_file_names)
    hazard_curves.to_json(file_name)

    return hazard_curves, source_branches


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logging.getLogger('pynamodb').setLevel(logging.DEBUG)
    logging.getLogger('toshi_hazard_store').setLevel(logging.DEBUG)

    nproc = 20
    classical = True

    vs30 = 400
    aggs = [
        'mean',
        0.005,
    ]  # 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 0.8, 0.9, 0.95, 0.975, 0.99, 0.995]

    # imts = ['PGA', 'SA(0.5)', 'SA(1.0)', 'SA(1.5)', 'SA(2.0)', 'SA(3.0)']
    imts = ['PGA', 'SA(0.5)', 'SA(1.5)', 'SA(3.0)']
    # imts = None

    # location_generator = locations_nzpt2_and_nz34_chunked
    # location_generator = locations_nz34_chunked
    location_generator = locations_nzpt2_chunked  # TODO: RANGED

    loc_keyrange = (0, 29)  # CDC
    loc_keyrange = (30, 45)  # CBC (there are 43, but just in case I miss counted)
    loc_keyrange = (0, 1)

    output_prefix = f'FullLT_{loc_keyrange[0]}_{loc_keyrange[1]}'

    hazard_curves, source_branches = process_agg(
        vs30,
        location_generator,
        aggs,
        imts,
        output_prefix=output_prefix,
        num_workers=nproc,
        location_range=loc_keyrange,
    )
