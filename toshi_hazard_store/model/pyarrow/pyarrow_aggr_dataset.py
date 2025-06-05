"""pyarrow helper function"""

import logging
import pathlib
import uuid
from functools import partial
from typing import TYPE_CHECKING, Iterable, Optional

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
from pyarrow import fs

from toshi_hazard_store.model.pyarrow.dataset_schema import get_hazard_aggregate_schema
from toshi_hazard_store.model.pyarrow.pyarrow_dataset import _write_metadata

log = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve


def append_models_to_dataset(
    models: Iterable['HazardAggregateCurve'],
    base_dir: str,
    dataset_format: str = 'parquet',
    filesystem: Optional[fs.FileSystem] = None,
    partitioning: Optional[Iterable[str]] = None,
    existing_data_behavior: str = "overwrite_or_ignore",
) -> None:
    """
    Write HazardAggregateCurve models to dataset.

    Args:
    models: An iterable of model data objects.
    base_dir: The path where the data will be stored.
    dataset_format (optional): The format of the dataset. Defaults to 'parquet'.
    filesystem (optional): The file system to use for storage. Defaults to None.
    partitioning (optional): The partitioning scheme to apply. Defaults to ['nloc_0'].
    existing_data_behavior: how to treat existing data (see pyarrow docs).

    Returns: None
    """
    item_dicts = [hag.model_dump() for hag in models]
    df = pd.DataFrame(item_dicts)

    # MANUALLY set the dataframe typing to match the pyarrow schema UGHHHH
    dtype = {
        "vs30": "int32",
    }
    df = df.astype(dtype)
    # coerce the the types UGGH
    df['values'] = df['values'].apply(lambda x: np.array(x, dtype=np.float32))

    log.debug("in df >>>")
    log.debug(df.info())
    log.debug("in df <<<")

    table = pa.Table.from_pandas(df)

    schema = get_hazard_aggregate_schema()
    using_s3 = isinstance(filesystem, fs.S3FileSystem)
    write_metadata_fn = partial(_write_metadata, using_s3, pathlib.Path(base_dir))
    ds.write_dataset(
        table,
        base_dir=base_dir,
        basename_template="%s-part-{i}.%s" % (uuid.uuid4(), dataset_format),
        partitioning=partitioning,
        partitioning_flavor="hive",
        existing_data_behavior=existing_data_behavior,
        format=dataset_format,
        file_visitor=write_metadata_fn,
        filesystem=filesystem,
        schema=schema,
    )
