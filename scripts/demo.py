"""Script to query toshi-hazard-store."""

import argparse
import collections
import datetime as dt
import json

from toshi_hazard_store.query_v3 import get_rlz_curves_v3

HazardRlz = collections.namedtuple('HazardRlz', 'nloc_001 tid vs30 rlz imt values tags ids')


def main():

    # locs = args.locs.split(',')
    # locs = [loc.replace('\\', '') for loc in locs]

    locs = [
        "-43.530~172.630",
    ]  # "-41.300~174.780", "-41.200~175.8"]
    tids = ["A_CRU", "A_PUY", "A_HIK"]
    vs30s = [750]
    imts = ['PGA']
    rlzs = None

    t0 = dt.datetime.utcnow()
    cnt = 0

    output = []
    for res in get_rlz_curves_v3(locs, vs30s, rlzs, tids, imts):
        # print(res)
        # print( res, res.created, res.source_tags, res.source_ids)
        values = res.values
        for rec in values:
            # print( rec.imt, rec.vals )
            h = HazardRlz(
                res.nloc_001,
                res.hazard_solution_id,
                res.vs30,
                res.rlz,
                rec.imt,
                rec.vals,
                list(res.source_tags),
                list(res.source_ids),
            )
            output.append(h._asdict())
            # print(h._asdict())
        cnt += 1

    # print(cnt, "Took %s secs" % (dt.datetime.utcnow() - t0).total_seconds())

    expected_sort_key = '-41.300~174.780:750:000000:A_CRU'
    expected_hash_key = '-41.3~174.8'

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
