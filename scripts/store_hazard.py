"""Script to export an openquake calculation and save it with toshi-hazard-store."""

import argparse

try:
    from openquake.commonlib import datastore

    from toshi_hazard_store.transform import export_meta, export_rlzs, export_rlzs_v2, export_stats
except ImportError:
    print("WARNING: the transform module uses the optional openquake dependencies - h5py, pandas and openquake.")
    raise

from toshi_hazard_store import model


def extract_and_save(args):
    """Do the work."""

    calc_id = int(args.calc_id)
    toshi_id = args.toshi_id
    skip_rlzs = args.skip_rlzs

    dstore = datastore.read(calc_id)
    oq = dstore['oqparam']

    R = len(dstore['full_lt'].get_realizations())

    # Save metadata record
    export_meta(toshi_id, dstore)

    # Hazard curves
    for kind in reversed(list(oq.get_kinds('', R))):  # do the stats curves first
        if kind.startswith('rlz-'):
            if skip_rlzs:
                continue
            export_rlzs(dstore, toshi_id, kind)
        else:
            export_stats(dstore, toshi_id, kind)

    # new RLZ storage
    if not skip_rlzs:
        export_rlzs_v2(dstore, toshi_id)

    dstore.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description='store_hazard.py (store_hazard)  - extract oq hazard by calc_id and store it.'
    )
    parser.add_argument('calc_id', help='openquake calc id.')
    parser.add_argument('toshi_id', help='openquake_hazard_solution id.')
    parser.add_argument('-c', '--create-tables', action="store_true", help="Ensure tables exist.")
    parser.add_argument('-k', '--skip_rlzs', action="store_true", help="Skip the realizations store.")
    # parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    # parser.add_argument("-s", "--summary", help="summarise output", action="store_true")
    parser.add_argument('-D', '--debug', action="store_true", help="print debug statements")
    args = parser.parse_args()
    return args


def handle_args(args):
    if args.debug:
        print(f"Args: {args}")

    if args.create_tables:
        print('Ensuring tables exist.')
        ## model.drop_tables() #DANGERMOUSE
        model.migrate()  # ensure model Table(s) exist (check env REGION, DEPLOYMENT_STAGE, etc

    extract_and_save(args)


def main():
    handle_args(parse_args())


if __name__ == '__main__':
    main()  # pragma: no cover
