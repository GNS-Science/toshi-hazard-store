"""pyarrow helper function"""

import logging
from typing import TYPE_CHECKING, Iterable, Optional

import numpy as np
import pandas as pd
import pyarrow as pa
from pyarrow import fs

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.model.pyarrow.dataset_schema import get_hazard_aggregate_schema

log = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve

hazard_agreggate_schema = get_hazard_aggregate_schema()


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
    table = table_from_models(models)
    pyarrow_dataset.append_models_to_dataset(
        table,
        base_dir,
        dataset_format,
        filesystem,
        partitioning,
        existing_data_behavior,
        schema=hazard_agreggate_schema,
    )


def table_from_models(models: Iterable['HazardAggregateCurve']) -> pa.Table:
    """build a pyarrow table from HazardAggregateCurve models.

    Args:
    models: An iterable of model data objects.

    Returns: The pyarrow hazard aggregations table.
    """

    df = pd.DataFrame([hazagg.model_dump() for hazagg in models])

    # MANUALLY set the dataframe typing to match the pyarrow schema UGHHHH
    dtype = {
        "vs30": "int32",
    }
    # coerce the the types
    df = df.astype(dtype)
    df['values'] = df['values'].apply(lambda x: np.array(x, dtype=np.float32))  # type: ignore
    return pa.Table.from_pandas(df)
