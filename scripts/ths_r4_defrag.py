"""
Console script for compacting THS rev4 parquet datasets
"""

import csv
import logging
import pathlib
import uuid
from functools import partial

import click
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
from pyarrow import fs

DATASET_FORMAT = 'parquet'  # TODO: make this an argument
MEMORY_WARNING_BYTES = 8e9  # At 8 GB let the user know they might run into trouble!!!

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


def human_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
    """Returns a human readable string representation of bytes"""
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])


def write_metadata(base_path, visited_file):
    meta = [
        pathlib.Path(visited_file.path).relative_to(base_path),
        visited_file.size,
    ]
    header_row = ["path", "size"]

    # NB metadata property does not exist for arrow format
    if visited_file.metadata:
        meta += [
            visited_file.metadata.format_version,
            visited_file.metadata.num_columns,
            visited_file.metadata.num_row_groups,
            visited_file.metadata.num_rows,
        ]
        header_row += ["format_version", "num_columns", "num_row_groups", "num_rows"]

    meta_path = pathlib.Path(visited_file.path).parent / "_metadata.csv"  # note prefix, otherwise parquet read fails
    write_header = False
    if not meta_path.exists():
        write_header = True
    with open(meta_path, 'a') as outfile:
        writer = csv.writer(outfile)
        if write_header:
            writer.writerow(header_row)
        writer.writerow(meta)
    log.debug(f"saved metadata to {meta_path}")


@click.command()
@click.argument('source')
@click.argument('target')
@click.option('-l', '--levels', help="how many folder levels to subdivide the source folder by", default=0)
@click.option("-p", "--parts", help="comma-separated list of partition keys", default="")
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-d', '--dry-run', is_flag=True, default=False)
def main(
    source,
    target,
    levels,
    parts,
    verbose,
    dry_run,
):
    """Compact the dataset within each partition.

    Can be used on both realisation and aggregate datasets.
    """
    source_folder = pathlib.Path(source)
    target_folder = pathlib.Path(target)
    target_parent = target_folder.parent

    assert source_folder.exists(), f'source {source_folder} is not found'
    assert source_folder.is_dir(), f'source {source_folder} is not a directory'

    assert target_parent.exists(), f'folder {target_parent} is not found'
    assert target_parent.is_dir(), f'folder {target_parent} is not a directory'

    partition_keys = [part.strip() for part in parts.split(",")] if parts else []

    if verbose:
        click.echo(f'using pyarrow version {pa.__version__}')
        click.echo(f"partitions: {partition_keys}")

    filesystem = fs.LocalFileSystem()
    writemeta_fn = partial(write_metadata, target_folder)
    dataset = ds.dataset(source_folder, filesystem=filesystem, format=DATASET_FORMAT, partitioning='hive')

    count = 0

    def source_folder_iterator(source_folder, levels):
        if levels == 0:
            yield source_folder
        elif levels == 1:
            for partition_folder in source_folder.iterdir():
                yield partition_folder
        else:
            raise NotImplementedError("max of one level is supported.")

    for partition_folder in source_folder_iterator(source_folder, levels):

        usage = sum(file.stat().st_size for file in partition_folder.rglob('*'))
        if usage > MEMORY_WARNING_BYTES:
            click.echo(f'partition {partition_folder} has size: {human_size(usage)}')
            click.confirm('Do you want to continue?', abort=True)
        elif verbose:
            click.echo(f'partition {partition_folder} has disk size: {human_size(usage)}')

        # TODO: this aproach doesn't handle different field types
        # _name, _value = partition_folder.name.split('=')
        # flt0 = pc.field(_name) == pc.scalar(_value)

        arrow_scanner = ds.Scanner.from_dataset(dataset)
        # tbl = arrow_scanner.to_table()
        # print(tbl)
        # assert 0
        ds.write_dataset(
            arrow_scanner,
            base_dir=str(target_folder),
            basename_template="%s-part-{i}.%s" % (uuid.uuid4(), DATASET_FORMAT),
            partitioning=partition_keys,
            partitioning_flavor="hive",
            existing_data_behavior="delete_matching",
            format=DATASET_FORMAT,
            file_visitor=writemeta_fn,
            max_rows_per_file=200 * 1024,
            max_rows_per_group=200 * 1024,
            min_rows_per_group=100 * 1024,
        )
        count += 1
        if verbose:
            click.echo(f'pyarrow RSS memory: {human_size(pa.total_allocated_bytes())}')

    click.echo(f'compacted {count} partitions for {target_folder.parent}')


if __name__ == "__main__":
    main()
