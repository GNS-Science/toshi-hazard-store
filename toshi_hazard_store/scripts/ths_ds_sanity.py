# flake8: noqa
"""
Console script for querying tables before and after import/migration to ensure that we have what we expect.

TODO this script needs a little housekeeping.
"""
import ast
import itertools
import json
import logging
import pathlib
import random

import click
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

log = logging.getLogger()

logging.basicConfig(level=logging.INFO)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('toshi_hazard_store').setLevel(logging.WARNING)

from nzshm_common import CodedLocation, LatLon, location
from nzshm_common.grids import load_grid
from nzshm_model import branch_registry
from nzshm_model.psha_adapter.openquake import gmcm_branch_from_element_text

import toshi_hazard_store  # noqa: E402
import toshi_hazard_store.config
import toshi_hazard_store.model.openquake_models
import toshi_hazard_store.model.revision_4.hazard_models  # noqa: E402
import toshi_hazard_store.query.hazard_query
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.oq_import.oq_manipulate_hdf5 import migrate_nshm_uncertainty_string
from toshi_hazard_store.scripts.core import echo_settings  # noqa

nz1_grid = load_grid('NZ_0_1_NB_1_1')
# print(location.get_location_list(["NZ"]))
city_locs = [LatLon(key.lat, key.lon) for key in location.get_location_list(["NZ"])]
srwg_locs = [LatLon(key.lat, key.lon) for key in location.get_location_list(["SRWG214"])]
IMTS = [
    'PGA',
    'SA(0.1)',
    'SA(0.15)',
    'SA(0.2)',
    'SA(0.25)',
    'SA(0.3)',
    'SA(0.35)',
    'SA(0.4)',
    'SA(0.5)',
    'SA(0.6)',
    'SA(0.7)',
    'SA(0.8)',
    'SA(0.9)',
    'SA(1.0)',
    'SA(1.25)',
    'SA(1.5)',
    'SA(1.75)',
    'SA(2.0)',
    'SA(2.5)',
    'SA(3.0)',
    'SA(3.5)',
    'SA(4.0)',
    'SA(4.5)',
    'SA(5.0)',
    'SA(6.0)',
    'SA(7.5)',
    'SA(10.0)',
]
all_locs = set(nz1_grid + srwg_locs + city_locs)

# print(nz1_grid[:10])
# print(srwg_locs[:10])
# print(city_locs[:10])

registry = branch_registry.Registry()


def get_random_args(gt_info, how_many):
    for n in range(how_many):
        yield dict(
            tid=random.choice(
                [
                    edge['node']['child']["hazard_solution"]["id"]
                    for edge in gt_info['data']['node']['children']['edges']
                ]
            ),
            imt=random.choice(IMTS),
            rlz=random.choice(range(20)),
            locs=[CodedLocation(o[0], o[1], 0.001) for o in random.sample(nz1_grid, how_many)],
        )


def query_table(args):
    for res in toshi_hazard_store.query.hazard_query.get_rlz_curves_v3(
        locs=[loc.code for loc in args['locs']], vs30s=[275], rlzs=[args['rlz']], tids=[args['tid']], imts=[args['imt']]
    ):
        yield (res)


def query_hazard_meta(args):
    for res in toshi_hazard_store.query.hazard_query.get_hazard_metadata_v3(haz_sol_ids=[args['tid']], vs30_vals=[275]):
        yield (res)


def get_table_rows(random_args_list):
    result = {}
    for args in random_args_list:
        meta = next(query_hazard_meta(args))
        gsim_lt = ast.literal_eval(meta.gsim_lt)
        src_lt = ast.literal_eval(meta.src_lt)
        assert len(src_lt['branch']) == 1

        # print(gsim_lt['uncertainty'])
        # source digest
        try:
            # handle the task T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU2MA== which has messed up meta...
            ids = [x for x in src_lt['branch']['A'].split('|') if x != '']
            srcs = "|".join(sorted(ids))
            src_id = registry.source_registry.get_by_identity(srcs)
        except Exception as exc:
            print(f'args: {args}')
            print()
            print(f'meta: {meta}')
            print()
            print(srcs)
            raise exc

        for res in query_table(args):
            obj = res.to_simple_dict(force=True)
            # gmm_digest
            gsim = gmcm_branch_from_element_text(
                migrate_nshm_uncertainty_string(gsim_lt['uncertainty'][str(obj['rlz'])])
            )
            # print(gsim)
            gsim_id = registry.gmm_registry.get_by_identity(gsim.registry_identity)

            obj['slt_sources'] = src_lt['branch']['A']
            obj['sources_digest'] = src_id.hash_digest
            obj['gsim_uncertainty'] = gsim
            obj['gmms_digest'] = gsim_id.hash_digest
            result[obj["sort_key"]] = obj
            # print()
            # print( obj )

    return result


def report_arrow_count_loc_rlzs(ds_name, location, verbose):
    """report on dataset realisations for a single location"""
    dataset = ds.dataset(f'{ds_name}/nloc_0={location.resample(1).code}', format='parquet')

    click.echo(f"querying arrow/parquet dataset {dataset}")
    flt = (pc.field('imt') == pc.scalar("PGA")) & (pc.field("nloc_001") == pc.scalar(location.code))
    # flt = pc.field("nloc_001")==pc.scalar(location.code)
    df = dataset.to_table(filter=flt).to_pandas()

    # get the unique hazard_calcluation ids...
    hazard_calc_ids = list(df.calculation_id.unique())

    if verbose:
        click.echo(hazard_calc_ids)
        click.echo
    count_all = 0
    for calc_id in hazard_calc_ids:
        df0 = df[df.calculation_id == calc_id]
        click.echo(f"-42.450~171.210, {calc_id}, {df0.shape[0]}")
        count_all += df0.shape[0]
    click.echo()
    click.echo(f"Grand total: {count_all}")


def report_v3_count_loc_rlzs(location, verbose):

    mRLZ = toshi_hazard_store.model.openquake_models.OpenquakeRealization

    gtfile = pathlib.Path(__file__).parent / "GT_HAZ_IDs_R2VuZXJhbFRhc2s6MTMyODQxNA==.json"
    gt_info = json.load(open(str(gtfile)))
    tids = [edge['node']['child']['hazard_solution']["id"] for edge in gt_info['data']['node']['children']['edges']]

    if verbose:
        click.echo(tids)
        click.echo()
    count_all = 0

    for tid in tids:
        rlz_count = mRLZ.count(
            location.resample(0.1).code,
            mRLZ.sort_key >= f'{location.code}:275:000000:{tid}',
            filter_condition=(mRLZ.nloc_001 == location.code) & (mRLZ.hazard_solution_id == tid),
        )
        count_all += rlz_count
        click.echo(f"{location.code}, {tid}, {rlz_count}")

    click.echo()
    click.echo(f"Grand total: {count_all}")
    return


def report_rlzs_grouped_by_partition(source: str, verbose, bail_on_error=True) -> int:
    """Report on dataset realisations by hive partion."""

    source_dir, source_filesystem = pyarrow_dataset.configure_output(source)

    dataset = ds.dataset(source_dir, filesystem=source_filesystem, format='parquet', partitioning='hive')

    def gen_filter(dataset):
        """Build filters from the dataset partioning."""

        def gen_filter_expr(dataset, partition_values):
            """build filter expression for each partition_layer"""
            for idx, fld in enumerate(dataset.partitioning.schema):
                yield pc.field(fld.name) == pc.scalar(partition_values[idx].as_py())

        for part_values in itertools.product(*dataset.partitioning.dictionaries):
            filters = gen_filter_expr(dataset, part_values)
            filter = None  # next(filters)
            for expr in filters:  # remaining
                filter = expr if filter is None else (filter & expr)
            yield filter

    def unique_permutations_series(series1, series2):
        return series1.combine(series2, lambda a, b: f"{a}:{b}")

    click.echo("filter, uniq_rlzs, uniq_locs, uniq_imts, uniq_src_gmms, uniq_vs30, consistent")
    click.echo("=============================================================================")

    count_all = 0
    for filter in gen_filter(dataset):

        df0 = dataset.to_table(filter=filter).to_pandas()
        unique_srcs_gmms = unique_permutations_series(df0.gmms_digest, df0.sources_digest)

        uniq_locs = len(list(df0.nloc_001.unique()))
        uniq_imts = len(list(df0.imt.unique()))
        uniq_srcs_gmms = len(list(unique_srcs_gmms.unique()))
        uniq_vs30 = len(list(df0.vs30.unique()))

        consistent = (uniq_locs * uniq_imts * uniq_srcs_gmms * uniq_vs30) == df0.shape[0]
        click.echo(f"{filter}, {df0.shape[0]}, {uniq_locs}, {uniq_imts}, {uniq_srcs_gmms}, {uniq_vs30}, {consistent}")
        count_all += df0.shape[0]

        if bail_on_error and not consistent:
            raise click.UsageError("The last filter realisation count was not consistent, aborting.")

    click.echo()
    click.echo(f"Realisations counted: {count_all}")
    return count_all


def report_v3_grouped_by_calc(verbose, bail_on_error=True):
    """report on dataset realisations"""
    mRLZ = toshi_hazard_store.model.openquake_models.OpenquakeRealization

    gtfile = pathlib.Path(__file__).parent / "GT_HAZ_IDs_R2VuZXJhbFRhc2s6MTMyODQxNA==.json"
    gt_info = json.load(open(str(gtfile)))
    calc_ids = [edge['node']['child']['hazard_solution']["id"] for edge in gt_info['data']['node']['children']['edges']]

    all_partitions = set([CodedLocation(lat=loc[0], lon=loc[1], resolution=0.1) for loc in list(all_locs)])
    if verbose:
        click.echo("Calc IDs")
        click.echo(calc_ids)
        click.echo()
        click.echo("Location Partitions")
        # click.echo(all_partitions)

    count_all = 0
    click.echo("calculation_id, uniq_rlzs, uniq_locs, uniq_imts, uniq_gmms, uniq_srcs, uniq_vs30, consistent")
    click.echo("============================================================================================")
    for calc_id in sorted(calc_ids):
        tid_count = 0
        tid_meta = dict(uniq_locs=set(), uniq_imts=set(), uniq_gmms=0, uniq_srcs=0, uniq_vs30s=0)
        sources = set([])
        gmms = set([])

        for partition in all_partitions:
            result = mRLZ.query(
                partition.resample(0.1).code,
                mRLZ.sort_key >= ' ',  # partition.resample(0.1).code[:3],
                filter_condition=(mRLZ.hazard_solution_id == calc_id) & (mRLZ.nloc_1 == partition.resample(0.1).code),
            )
            # print(partition.resample(1).code)
            for res in result:
                assert len(res.values) == 27
                imt_count = len(res.values)
                tid_count += imt_count
                count_all += imt_count
                tid_meta['uniq_locs'].add(res.nloc_001)
                tid_meta['uniq_imts'].update(set([v.imt for v in res.values]))
                gmms.add(res.rlz)

        tid_meta['uniq_gmms'] += len(gmms)
        click.echo(
            f"{calc_id}, {tid_count}, {len(tid_meta['uniq_locs']) }, {len(tid_meta['uniq_imts'])}, {tid_meta['uniq_gmms']}, "
            f" - ,  - , - "
        )

        # click.echo(
        #     f"{calc_id}, {df0.shape[0]}, {uniq_locs}, {uniq_imts}, {uniq_gmms}, {uniq_srcs}, {uniq_vs30}, {consistent}"
        # )
        # count_all += df0.shape[0]

        # if bail_on_error and not consistent:
        #     return

    click.echo()
    click.echo(f"Grand total: {count_all}")
    return


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|


@click.group()
@click.pass_context
def main(context):
    """Import NSHM Model hazard curves to new revision 4 models."""

    context.ensure_object(dict)
    # context.obj['work_folder'] = work_folder


@main.command()
@click.argument('source', type=str)
@click.option('-x', '--strict', is_flag=True, default=False, help="abort if consistency checks fail")
@click.option('-ER', '--expected-rlzs', default=0, type=int)
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-d', '--dry-run', is_flag=True, default=False)
@click.pass_context
def count_rlz(context, source, strict, expected_rlzs, verbose, dry_run):
    """Count the realisations from SOURCE by calculation id"""
    if verbose:
        click.echo(f"NZ 0.1grid has {len(nz1_grid)} locations")
        click.echo(f"All (0.1 grid + SRWG + NZ) has {len(all_locs)} locations")
        click.echo(f"All (0.1 grid + SRWG) has {len(nz1_grid + srwg_locs)} locations")
        click.echo()

    rlz_count = report_rlzs_grouped_by_partition(source, verbose, bail_on_error=strict)
    if expected_rlzs and not rlz_count == expected_rlzs:
        raise click.UsageError(
            f"The count of realisations: {rlz_count} doesn't match specified expected_rlzs: {expected_rlzs}"
        )

    # TODO: the  following may still be useful for a little while, but should be moved into
    # a separate sub-command
    # # location = CodedLocation(lat=-39, lon=175.93, resolution=0.001)
    # location = CodedLocation(lat=-41, lon=175, resolution=0.001)

    # if (source_type == 'ARROW') and source:
    #     if report == 'LOC':
    #         report_arrow_count_loc_rlzs(source, location, verbose)
    #
    # if source == 'AWS':
    #     if report == 'LOC':
    #         report_v3_count_loc_rlzs(location, verbose)
    #     elif report == 'ALL':
    #         report_v3_grouped_by_calc(verbose, bail_on_error=strict)


@main.command()
@click.argument('dataset', type=str)
@click.argument('count', type=int)
@click.option('--iterations', '-i', type=int, default=1)
@click.option('-df', '--defragged', is_flag=True, default=False, help="use defragged partition structure")
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.pass_context
def random_rlz_new(context, dataset, count, iterations, defragged, verbose):
    """Randomly select realisations from Dynamodb and compare with dataset values."""

    dataset_folder = pathlib.Path(dataset)
    assert dataset_folder.exists(), 'dataset not found'

    # TODO: this needs to handle any GT
    gtfile = pathlib.Path(__file__).parent / "migration" / "GT_HAZ_IDs_R2VuZXJhbFRhc2s6MTMyODQxNA==.json"
    gt_info = json.load(open(str(gtfile)))

    all_checked = 0
    for iteration in range(iterations):

        random_args_list = list(get_random_args(gt_info, count))

        if verbose:
            click.echo(f'Iteration: {iteration}')
            click.echo('===============')

        dynamodb_set = get_table_rows(random_args_list)
        iteration_checked = 0
        for key, obj in dynamodb_set.items():
            if verbose:
                click.echo(f"dynamo key: {key}")

            if defragged:
                segment = f"vs30={obj['vs30']}/nloc_0={obj['nloc_0']}"
            else:
                segment = f"nloc_0={obj['nloc_0']}"

            dataset = ds.dataset(dataset_folder / segment, format='parquet', partitioning='hive')
            for value in obj['values']:

                flt = (
                    (pc.field("nloc_001") == obj['nloc_001'])
                    & (pc.field("imt") == value['imt'])
                    & (pc.field('calculation_id') == obj['hazard_solution_id'])
                    & (pc.field('gmms_digest') == obj['gmms_digest'].replace('|', ''))
                )
                # (pc.field("vs30") == obj['vs30']) &\
                if verbose:
                    click.echo(f" ds filter: {flt}")

                df = dataset.to_table(filter=flt).to_pandas()
                if not (df.iloc[0]['values'] == np.array(value['vals'])).all():
                    click.echo(key, obj)
                    click.echo()
                    click.echo(value['imt'], value['vals'])
                    click.echo("FAIL")
                    assert 0

                iteration_checked += 1
                all_checked += 1

        if verbose:
            click.echo()
            click.echo(f'Checked {iteration_checked} random value arrays from {flt}.')
            click.echo()

    if verbose:
        click.echo(f'Checked {all_checked} random value arrays in total.')


if __name__ == "__main__":
    main()
