"""pyarrow helper function"""

import csv
import logging
import pathlib
import uuid
from functools import partial
from typing import Callable, List, Optional, Union

import pyarrow as pa
import pyarrow.dataset
import pyarrow.dataset as ds
import s3path
from pyarrow import fs

log = logging.getLogger(__name__)


def write_metadata(
    is_s3: bool, output_folder: pathlib.Path, visited_file: pyarrow.dataset.WrittenFile
) -> None:  # pragma: no cover

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
    partitioning: Optional[List[str]] = None,
):
    """
    append realisation models to dataset using the pyarrow library

    TODO: option to BAIL if realisation exists, assume this is a duplicated operation
    TODO: schema checks
    """
    partitioning = partitioning or ['nloc_0']

    # hack for now ....
    if base_dir[:2] == '//':
        base_dir = base_dir[2:]

    is_s3 = isinstance(filesystem, fs.S3FileSystem)
    write_metadata_fn = partial(write_metadata, is_s3, pathlib.Path(base_dir))

    ds.write_dataset(
        table_or_batchreader,
        base_dir=base_dir,
        basename_template="%s-part-{i}.%s" % (uuid.uuid4(), dataset_format),
        partitioning=partitioning,
        partitioning_flavor="hive",
        existing_data_behavior="overwrite_or_ignore",
        format=dataset_format,
        file_visitor=write_metadata_fn,
        filesystem=filesystem,
    )
