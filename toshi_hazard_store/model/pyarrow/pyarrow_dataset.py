"""pyarrow helper functions"""

import csv
import logging
import os
import pathlib
import uuid
from functools import partial
from typing import Callable, Iterable, Optional, Tuple, Union

import pyarrow as pa
import pyarrow.dataset
import pyarrow.dataset as ds
import s3path
from pyarrow import fs

REGION = os.getenv('REGION', 'ap-southeast-2')  # SYDNEY

log = logging.getLogger(__name__)


def _write_metadata(
    is_s3: bool, output_folder: pathlib.Path, visited_file: pyarrow.dataset.WrittenFile
) -> None:  # pragma: no cover
    """Write to _metadata.csv based on the visited_file."""

    log.info(f'write_metadata() called with is_s3: {is_s3} {output_folder}, {visited_file.path}')

    path_class: Callable
    if is_s3:
        path_class = s3path.S3Path
    else:
        path_class = pathlib.Path

    output_folder = path_class(output_folder)

    visited_file_path = path_class(visited_file.path)
    if not visited_file_path.is_absolute():
        visited_file_path = path_class('/') / visited_file_path
        assert visited_file_path.is_absolute()

    if not output_folder.is_absolute():
        output_folder = path_class('/') / output_folder
        assert output_folder.is_absolute()

    meta = [
        visited_file_path.relative_to(output_folder),
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

    log.info(f'visited_file.path: {visited_file_path}')
    meta_path = visited_file_path.parent / "_metadata.csv"
    log.info(f'meta_path: {meta_path}')

    write_header = False
    if meta_path.exists():
        # for S3 where we can't append
        with meta_path.open('rb') as old_meta:
            meta_now = old_meta.read().decode()  # read the current content
        meta_path.unlink()  # delete (maybe not necessary )
    else:
        write_header = True

    if is_s3:  # sadly the open signature is not compatible :(
        outfile = meta_path.open('wb', newline='', encoding='utf8')
    else:
        outfile = meta_path.open('w')

    # csv.writer will write corre
    writer = csv.writer(outfile)
    if write_header:
        writer.writerow(header_row)
    else:
        # there was old metadata, so write that out first
        outfile.write(meta_now)
    writer.writerow(meta)  # and finally append the new meta
    log.debug(f"saved metadata to {meta_path}")


def append_models_to_dataset(
    table_or_batchreader: Union[pa.Table, pa.RecordBatchReader],
    base_dir: str,
    dataset_format: str = 'parquet',
    filesystem: Optional[fs.FileSystem] = None,
    partitioning: Optional[Iterable[str]] = None,
    existing_data_behavior: str = "overwrite_or_ignore",
) -> None:
    """
    Appends realisations to a dataset using the pyarrow library.

    Args:
    table_or_batchreader: A pyarrow Table or RecordBatchReader.
    base_dir: The path where the data will be stored.
    dataset_format (optional): The format of the dataset. Defaults to 'parquet'.
    filesystem (optional): The file system to use for storage. Defaults to None.
    partitioning (optional): The partitioning scheme to apply. Defaults to ['nloc_0'].
    existing_data_behavior: how to treat existing data (see pyarrow docs).

    Returns: None

    Raises:
        TypeError: If an invalid data source is provided.
    """
    if not isinstance(table_or_batchreader, (pa.Table, pa.RecordBatchReader)):
        raise TypeError("table_or_batchreader must be a pyarrow Table or RecordBatchReader")

    partitioning = partitioning or ['nloc_0']
    using_s3 = isinstance(filesystem, fs.S3FileSystem)

    write_metadata_fn = partial(_write_metadata, using_s3, pathlib.Path(base_dir))
    ds.write_dataset(
        table_or_batchreader,
        base_dir=base_dir,
        basename_template="%s-part-{i}.%s" % (uuid.uuid4(), dataset_format),
        partitioning=partitioning,
        partitioning_flavor="hive",
        existing_data_behavior=existing_data_behavior,
        format=dataset_format,
        file_visitor=write_metadata_fn,
        filesystem=filesystem,
    )


def configure_output(output_target: str) -> Tuple[str, fs.FileSystem]:
    """
    Configure the output for a given path.

    Determines whether the output is an S3 URI or a local path and returns the relevant filesystem
    and output path.

    Args:
        output_target (str): The output path to configure.

    Returns:
        tuple: A tuple containing the absolute output path and the corresponding filesystem.
    """
    if output_target.startswith('s3://'):
        # We have an AWS S3 URI
        output = str(s3path.PureS3Path.from_uri(output_target))
        log.info(f'using S3 output with path: `{output}` and region: `{REGION}`')
        filesystem = fs.S3FileSystem(region=REGION)
        output = output[1:]  # we expect this to work for pyarrow datasets, which need '/' prefix stripped
    else:
        # We have a local path
        output = str(pathlib.Path(output_target).resolve())
        filesystem = fs.LocalFileSystem()
    return output, filesystem
