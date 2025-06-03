"""
Console script for compacting THS parquet datasets
"""

import csv
import logging
import pathlib

import click
import pyarrow as pa
import pyarrow.dataset as ds

from toshi_hazard_store.model.pyarrow import pyarrow_dataset

DATASET_FORMAT = 'parquet'  # TODO: make this an argument

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
@click.option("-p", "--parts", help="comma-separated list of partition keys for the target DS", default="vs30,nloc_0")
@click.option('-v', '--verbose', is_flag=True, default=False)
def main(
    source,
    target,
    parts,
    verbose,
):
    """Compact and repartition the dataset.

    Can be used on both realisation and aggregate datasets.

    Arguments:\n

    SOURCE: path to the source (folder OR S3 URI).\n
    TARGET: path to the target (folder OR S3 URI).
    """

    source_dir, source_filesystem = pyarrow_dataset.configure_output(source)
    target_dir, target_filesystem = pyarrow_dataset.configure_output(target)

    partition_keys = [part.strip() for part in parts.split(",")] if parts else []

    if verbose:
        click.echo(f'using pyarrow version {pa.__version__}')
        click.echo(f"partitions: {partition_keys}")
        click.echo(f"source: `{source_dir}` using fs:{source_filesystem}")
        click.echo(f"target: `{target_dir}` using fs:{target_filesystem}")

    dataset = ds.dataset(source_dir, filesystem=source_filesystem, format=DATASET_FORMAT, partitioning='hive')
    arrow_scanner = ds.Scanner.from_dataset(dataset)

    pyarrow_dataset.append_models_to_dataset(
        arrow_scanner.to_reader(),
        base_dir=target_dir,
        filesystem=target_filesystem,
        partitioning=partition_keys,
        existing_data_behavior="delete_matching",
    )

    # OLD SETUP, wes more specific about limits etc,
    # and we may still need some of this in the above method
    #
    # ds.write_dataset(
    #     arrow_scanner,
    #     base_dir=str(target_dir),
    #     basename_template="%s-part-{i}.%s" % (uuid.uuid4(), DATASET_FORMAT),
    #     partitioning=partition_keys,
    #     partitioning_flavor="hive",
    #     existing_data_behavior="delete_matching",
    #     format=DATASET_FORMAT,
    #     # file_visitor=writemeta_fn,
    #     max_rows_per_file=200 * 1024,
    #     max_rows_per_group=200 * 1024,
    #     min_rows_per_group=100 * 1024,
    #     filesystem=target_filesystem
    # )


if __name__ == "__main__":
    main()
