"""
Console script for comparing datasets for content equivalence.
"""

import logging
import pathlib
import random

import click
import pyarrow.compute as pc
import pyarrow.dataset as ds

log = logging.getLogger()

logging.basicConfig(level=logging.INFO)

DATASET_FORMAT = 'parquet'  # TODO: make this an argument
MEMORY_WARNING_BYTES = 8e9  # At 8 GB let the user know they might run into trouble!!!


def human_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
    """Returns a human readable string representation of bytes"""
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|
@click.group()
@click.pass_context
def main(context):
    """Compare NSHM Model hazard datasets."""

    context.ensure_object(dict)


def source_folder_iterator(source_folder, levels):
    """Yields a sequence of source folders.

    Args:
        source_folder (pathlib.Path): The source folder to iterate over.
        levels (int): The number of partition (folder) levels to subdivide the source folder by.

    Yields:
        str: A string representation of the current partition folder(s).

    Raises:
        NotImplementedError: If more than two levels are specified.
    """
    if levels == 0:
        yield source_folder
    elif levels == 1:
        for partition_folder in source_folder.iterdir():
            yield partition_folder.name
    elif levels == 2:
        for folder in source_folder.iterdir():
            for partition_folder in folder.iterdir():
                yield f"{folder.name}/{partition_folder.name}"
    else:
        raise NotImplementedError("max of two levels is supported.")


@main.command()
@click.argument('dataset0', type=str)
@click.argument('dataset1', type=str)
@click.option('-l', '--levels', help="how many partition (folder) levels to subdivide the source folder by", default=0)
@click.option('-cid', '--calc-id', default=None)
@click.option('--count', '-n', type=int, default=10)
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-x', '--exit-on-error', is_flag=True, default=False)
@click.pass_context
def rlzs(context, dataset0, dataset1, levels, calc_id, count, verbose, exit_on_error):
    """randomly select realisations loc, hazard_id, rlz, source and compare the results

    between two rlz datasetsn both having the hive layers: vs30, nloc_0.
    """

    folder0 = pathlib.Path(dataset0)
    folder1 = pathlib.Path(dataset1)

    assert folder0.exists(), f'dataset not found: {dataset0}'
    assert folder1.exists(), f'dataset not found: {dataset1}'

    src_folders = random.choices(population=[s for s in source_folder_iterator(folder0, levels)], k=5)

    all_checked = 0
    for sub_folder in src_folders:

        source_folder_a, source_folder_b = (folder0 / sub_folder), (folder1 / sub_folder)

        assert source_folder_a.exists()
        assert source_folder_b.exists()

        usage = sum(file.stat().st_size for file in source_folder_a.rglob('*'))
        if usage > MEMORY_WARNING_BYTES:
            click.echo(f'partition {source_folder_a} has size: {human_size(usage)}.')
            click.echo('NB. you can use the `--levels` argument to divide this job into smaller chunks.')
            click.confirm('Do you want to continue?', abort=True)
        elif verbose:
            click.echo(f'partition {source_folder_a} has disk size: {human_size(usage)}')

        # random_args_list = list(get_random_args(gt_info, count))
        ds0 = ds.dataset(source_folder_a, format='parquet', partitioning='hive')
        ds1 = ds.dataset(source_folder_b, format='parquet', partitioning='hive')

        df = ds0.to_table().to_pandas()

        imts = df['imt'].unique().tolist()
        nloc_3s = df['nloc_001'].unique().tolist()
        src_digests = df['sources_digest'].unique().tolist()

        ## Random checks
        partition_checked = 0
        for i in range(count):

            imt = random.choice(imts)
            nloc_3 = random.choice(nloc_3s)
            src_digest = random.choice(src_digests)

            flt = (
                (pc.field("nloc_001") == nloc_3) & (pc.field("imt") == imt) & (pc.field('sources_digest') == src_digest)
            )
            if calc_id:
                flt = flt & (pc.field("calculation_id") == calc_id)

            if verbose:
                click.echo(f'Checking values for {flt}')

            df0 = ds0.to_table(filter=flt).to_pandas().set_index('rlz').sort_index()
            df1 = ds1.to_table(filter=flt).to_pandas().set_index('rlz').sort_index()

            for idx in range(df0.shape[0]):
                l0 = df0.iloc[idx]['values']
                l1 = df1.iloc[idx]['values']
                if not (l0 == l1).all():
                    click.echo("\tl0 and l1 differ... ")
                    click.echo((l0 == l1))

                    click.echo()
                    click.echo(f'\tl0: {df0.iloc[idx]}')
                    click.echo()
                    click.echo(f'\tl1: {df1.iloc[idx]}')

                    if exit_on_error:
                        raise ValueError()

                partition_checked += 1
                all_checked += 1

        if verbose:
            click.echo(f'Checked {partition_checked} random value arrays from {flt}.')

    if verbose:
        click.echo(f'Checked {all_checked} random value arrays in total.')


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
    # nloc_3s0 = df0['nloc_001'].unique().tolist()
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
                print("l0 and l1 differ... ")
                print((l0 == l1))

                print()
                print(f'l0: {df0.iloc[idx]}')
                print()
                print(f'l1: {df1.iloc[idx]}')

                assert 0


if __name__ == "__main__":
    main()
