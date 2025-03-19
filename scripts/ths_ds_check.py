"""
Console script for comparing datasets for content equivalence.
"""

import ast
import importlib
import itertools
import json
import logging
import pathlib
import random

import click
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

log = logging.getLogger()

logging.basicConfig(level=logging.INFO)


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|
@click.group()
@click.pass_context
def main(context):
    """Compare NSHM Model hazard datasets."""

    context.ensure_object(dict)


@main.command()
@click.argument('dataset0', type=str)
@click.argument('dataset1', type=str)
@click.option('--count', '-n', type=int, default=10)
@click.pass_context
def rlzs(context, dataset0, dataset1, count):
    """randomly select realisations loc, hazard_id, rlz, source and compare the results

    between two rlz datasets having the hive layers: vs30, nloc_0.
    """

    folder0 = pathlib.Path(dataset0)
    folder1 = pathlib.Path(dataset1)
    assert folder0.exists(), f'dataset not found: {dataset0}'
    assert folder1.exists(), f'dataset not found: {dataset1}'

    # random_args_list = list(get_random_args(gt_info, count))
    segment = 'vs30=275/nloc_0=-37.0~174.0'
    ds0 = ds.dataset(folder0 / segment, format='parquet', partitioning='hive')
    ds1 = ds.dataset(folder1 / segment, format='parquet', partitioning='hive')

    df = ds0.to_table().to_pandas()
    imts = df['imt'].unique().tolist()
    nloc_3s = df['nloc_001'].unique().tolist()
    # rlzs = df['rlz'].unique().tolist()
    src_digests = df['sources_digest'].unique().tolist()

    ## Random checks
    for i in range(count):

        imt = random.choice(imts)
        # rlz = random.choice(rlzs[:11])
        nloc_3 = random.choice(nloc_3s)
        src_digest = random.choice(src_digests)

        flt = (pc.field("nloc_001") == nloc_3) & (pc.field("imt") == imt) & (pc.field('sources_digest') == src_digest)
        # (pc.field('rlz') == rlz) &\

        df0 = ds0.to_table(filter=flt).to_pandas().set_index('rlz').sort_index()
        df1 = ds1.to_table(filter=flt).to_pandas().set_index('rlz').sort_index()

        for idx in range(df0.shape[0]):
            l0 = df0.iloc[idx]['values']
            l1 = df1.iloc[idx]['values']
            if not (l0 == l1).all():
                print(f"l0 and l1 differ... ")
                print((l0 == l1))

                print()
                print(f'l0: {df0.iloc[idx]}')
                print()
                print(f'l1: {df1.iloc[idx]}')

                assert 0


@main.command()
@click.argument('dataset0', type=str)
@click.argument('dataset1', type=str)
@click.option('--count', '-n', type=int, default=10)
@click.pass_context
def aggs(context, dataset0, dataset1, count):
    """randomly select THP aggs loc, hazard_id, rlz, source and compare the results

    between two agg datasets having the hive layers
    """

    folder0 = pathlib.Path(dataset0)
    folder1 = pathlib.Path(dataset1)
    assert folder0.exists(), f'dataset not found: {dataset0}'
    assert folder1.exists(), f'dataset not found: {dataset1}'

    # random_args_list = list(get_random_args(gt_info, count))
    # segment = 'vs30=275/nloc_0=-38.0~177.0'
    ds0 = ds.dataset(folder0, format='parquet', partitioning='hive')
    ds1 = ds.dataset(folder1, format='parquet', partitioning='hive')

    df0 = ds0.to_table().to_pandas()
    df1 = ds1.to_table().to_pandas()

    imts = df1['imt'].unique().tolist()
    nloc_3s0 = df0['nloc_001'].unique().tolist()
    nloc_3s1 = df1['nloc_001'].unique().tolist()

    # print(f'nloc_3s0: {nloc_3s0}')
    # print(f'nloc_3s1: {nloc_3s1}')
    # rlzs = df['rlz'].unique().tolist()
    aggs = list(set(df1['agg'].unique().tolist()).intersection(set(df0['agg'].unique().tolist())))

    ## Random checks
    for i in range(count):

        imt = random.choice(imts)
        nloc_3 = random.choice(nloc_3s1)
        # agg = random.choice(aggs)

        flt = (pc.field("nloc_001") == nloc_3) & (pc.field("imt") == imt) & (pc.field('agg').isin(aggs))

        df0 = ds0.to_table(filter=flt).to_pandas().set_index('agg').sort_index()
        # print(df0)

        df1 = ds1.to_table(filter=flt).to_pandas().set_index('agg').sort_index()
        # print(df1)

        assert df0.shape == df1.shape

        for idx in range(df0.shape[0]):
            l0 = df0.iloc[idx]['values']
            l1 = df1.iloc[idx]['values']
            if not (l0 == l1).all():
                print(f"l0 and l1 differ... ")
                print((l0 == l1))

                print()
                print(f'l0: {df0.iloc[idx]}')
                print()
                print(f'l1: {df1.iloc[idx]}')

                assert 0


if __name__ == "__main__":
    main()
