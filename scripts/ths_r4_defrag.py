# flake8: noqa
"""
Console script for compacting THS rev4 parquet datasets
"""

import csv
import logging
import pathlib
import uuid
from functools import partial

import click
import pandas as pd

import pyarrow.dataset as ds
from pyarrow import fs

DATASET_FORMAT = 'parquet'  # TODO: make this an argument

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

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
@click.option("-p", "--parts", help="comma-separated list of partition keys", default="")
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-d', '--dry-run', is_flag=True, default=False)
def main(
    source,
    target,
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
        click.echo(f"partitions: {partition_keys}")

    # no optimising parallel stuff yet
    filesystem = fs.LocalFileSystem()
    dataset = ds.dataset(source_folder, filesystem=filesystem, format=DATASET_FORMAT, partitioning='hive')

    writemeta_fn = partial(write_metadata, target_folder)

    count = 0
    for partition_folder in source_folder.iterdir():
        if verbose:
            click.echo(f'partition {partition_folder}')

        arrow_scanner = ds.Scanner.from_dataset(dataset)
        ds.write_dataset(
            arrow_scanner,
            base_dir=str(target_folder),
            basename_template="%s-part-{i}.%s" % (uuid.uuid4(), DATASET_FORMAT),
            partitioning=partition_keys,
            partitioning_flavor="hive",
            existing_data_behavior="delete_matching",
            format=DATASET_FORMAT,
            file_visitor=writemeta_fn,
        )
        count += 1
        if verbose:
            click.echo(f'compacted {target_folder}')

    click.echo(f'compacted {count} partitions for {target_folder.parent}')


if __name__ == "__main__":
    main()
