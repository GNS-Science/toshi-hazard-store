"""pyarrow helper function"""

import logging
from typing import TYPE_CHECKING, Iterable, Optional

import pandas as pd
import pyarrow as pa
from pyarrow import fs

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.model.pyarrow.dataset_schema import get_hazard_aggregate_schema

log = logging.getLogger(__name__)

if TYPE_CHECKING:
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
    """

    item_dicts = [hag.model_dump() for hag in models]
    df = pd.DataFrame(item_dicts)
    table = pa.Table.from_pandas(df)

    pyarrow_dataset.append_models_to_dataset(
        table_or_batchreader=table,
        base_dir=base_dir,
        filesystem=filesystem,
        partitioning=partitioning,
        dataset_format=dataset_format,
        existing_data_behavior=existing_data_behavior,
        schema=get_hazard_aggregate_schema(),
    )
