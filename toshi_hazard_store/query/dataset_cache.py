"""Dataset caching functionality for hazard queries."""

import datetime as dt
import logging
from functools import lru_cache

import pyarrow.dataset as ds

from toshi_hazard_store.config import DATASET_AGGR_URI
from toshi_hazard_store.model.gridded.gridded_hazard_pydantic import (
    GriddedHazardPoeLevels,
)
from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.query.hazard_query import downsample_code

log = logging.getLogger(__name__)

GB = 1024**3


@lru_cache(maxsize=1)
def get_dataset() -> ds.Dataset:
    """
    Cache the dataset.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(
            DATASET_AGGR_URI
        )
        dataset = ds.dataset(
            source_dir,
            filesystem=source_filesystem,
            partitioning="hive",
            format="parquet",
            schema=HazardAggregateCurve.pyarrow_schema(),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset: {e}")
    return dataset


@lru_cache(maxsize=1)
def get_gridded_dataset(dataset_uri) -> ds.Dataset:
    start_time = dt.datetime.now()
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(dataset_uri)
        dataset = ds.dataset(
            source_dir,
            filesystem=source_filesystem,
            partitioning="hive",
            format="parquet",
            schema=GriddedHazardPoeLevels.pyarrow_schema(),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset: {e}")
    return dataset


@lru_cache(maxsize=3)
def get_dataset_vs30(vs30: int) -> ds.Dataset:
    """
    Cache the dataset for a given vs30.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(
            DATASET_AGGR_URI
        )
        dspath = f"{source_dir}/vs30={vs30}"
        dataset = ds.dataset(
            dspath,
            filesystem=source_filesystem,
            partitioning="hive",
            format="parquet",
            schema=HazardAggregateCurve.pyarrow_schema(),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset: {e}")
    return dataset


@lru_cache(maxsize=32)
def get_dataset_vs30_nloc0(vs30: int, nloc: str) -> ds.Dataset:
    """
    Cache the dataset for a given vs30 and nloc_0.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(
            DATASET_AGGR_URI
        )
        log.debug(f"source_dir:`{source_dir}`, filesystem: `{source_filesystem}`")
        dspath = f"{source_dir}/vs30={vs30}/nloc_0={downsample_code(nloc, 1.0)}"
        log.debug(f"Opening dspath :`{dspath}`")
        dataset = ds.dataset(
            dspath,
            filesystem=source_filesystem,
            partitioning="hive",
            format="parquet",
            schema=HazardAggregateCurve.pyarrow_schema(),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset: {e}")
    return dataset
