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

        consistent = (uniq_locs * uniq_imts * uniq_srcs_gmms) == df0.shape[0]
        click.echo(f"{filter}, {df0.shape[0]}, {uniq_locs}, {uniq_imts}, {uniq_srcs_gmms}, {uniq_vs30}, {consistent}")
        count_all += df0.shape[0]

        if bail_on_error and not consistent:
            raise click.UsageError("The last filter realisation count was not consistent, aborting.")

    click.echo()
    click.echo(f"Realisations counted: {count_all}")
    return count_all


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


if __name__ == "__main__":
    main()
