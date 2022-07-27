"""Test aggregatio core binning aggregation. """

import json
import sys
import unittest
from pathlib import Path

from toshi_hazard_store.aggregate_rlzs import get_imts, get_levels, process_location_list
from toshi_hazard_store.branch_combinator.branch_combinator import get_weighted_branches, grouped_ltbs, merge_ltbs
from toshi_hazard_store.locations import locations_nzpt2_and_nz34_binned, locations_nzpt2_and_nz34_chunked

# from toshi_hazard_store.branch_combinator.SLT_37_GRANULAR_RELEASE_1 import logic_tree_permutations
# from toshi_hazard_store.branch_combinator.SLT_37_GT_VS400_gsim_DATA import data as gtdata


class TestBuildAggregation(unittest.TestCase):
    """This test class disables openquake for testing, even if it's actually installed."""

    def setUp(self):
        self._sb_file = Path(Path(__file__).parent, 'fixtures/aggregation', 'source_branches.json')
        self._ltb_file = Path(Path(__file__).parent, 'fixtures/aggregation', 'SLT_TAG_FINAL.json')

    def tearDown(self):
        if self._temp_oq:
            sys.modules['openquake'] = self._temp_oq
        else:
            del sys.modules['openquake']

    @unittest.skip("THis is actually pulling down realizations")
    def test_core_function(self):
        """Based on aggregate_rlzs:main."""

        ltb_data = json.load(open(self._ltb_file, 'r'))
        logic_tree_permutations = ltb_data['logic_tree_permutations']
        gtdata = ltb_data['hazard_solutions']

        vs30 = 400
        aggs = ['mean', 0.05, 0.1, 0.2, 0.5, 0.8, 0.9, 0.95]

        omit: List[str] = []
        toshi_ids = [b.hazard_solution_id for b in merge_ltbs(logic_tree_permutations, gtdata=gtdata, omit=omit)]

        # grouped = grouped_ltbs(merge_ltbs(logic_tree_permutations, gtdata=gtdata, omit=omit))

        weighted_source_branches = json.load(open(self._sb_file, 'r'))

        binned_locs = locations_nzpt2_and_nz34_chunked(grid_res=1.0, point_res=0.001)
        levels = get_levels(
            weighted_source_branches, list(binned_locs.values())[0], vs30
        )  # TODO: get seperate levels for every IMT

        imts = ['PGA']
        # imts = get_imts(weighted_source_branches, vs30)
        levels = get_levels(
            weighted_source_branches, list(binned_locs.values())[0], vs30
        )  # TODO: get seperate levels for every IMT

        columns = ['lat', 'lon', 'imt', 'agg', 'level', 'hazard']
        # index = range(len(locs)*len(imts)*len(aggs)*len(levels))
        # hazard_curves = pd.DataFrame(columns=columns)

        # # tic = time.perf_counter()
        # for i in range(len(source_branches)):
        #     rlz_combs, weight_combs = build_rlz_table(source_branches[i], vs30)
        #     source_branches[i]['rlz_combs'] = rlz_combs
        #     source_branches[i]['weight_combs'] = weight_combs
        # toc = time.perf_counter()
        # print(f'time to build all realization tables {toc-tic:.1f} seconds')

        for key, locs in locations_nzpt2_and_nz34_binned(grid_res=1.0, point_res=0.001).items():
            binned_hazard_curves = process_location_list(
                locs[:1], toshi_ids, weighted_source_branches, aggs, imts[:1], levels, vs30
            )
            break
            # binned_hazard_curves.to_json(f"./df_{key}_aggregates.json")
            # hazard_curves = pd.concat([hazard_curves, binned_hazard_curves])

        assert 0
