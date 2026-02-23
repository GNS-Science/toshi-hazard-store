"""Dataset caching functionality for hazard queries."""

import datetime as dt
import logging
from functools import lru_cache
from typing import Optional

import pyarrow.dataset as ds

from toshi_hazard_store.config import DATASET_AGGR_URI, DATASET_GRIDDED_URI
from toshi_hazard_store.model.gridded.gridded_hazard_pydantic import GriddedHazardPoeLevels
from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.query.hazard_query import downsample_code

log = logging.getLogger(__name__)

GB = 1024**3


@lru_cache(maxsize=1)
def get_dataset(dataset_uri: Optional[str] = None) -> ds.Dataset:
    """
    Cache the dataset.

    Args:
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    ds_uri = dataset_uri or DATASET_AGGR_URI
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(ds_uri)
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
def get_gridded_dataset(dataset_uri: Optional[str] = None) -> ds.Dataset:
    start_time = dt.datetime.now()
    ds_uri = dataset_uri or DATASET_GRIDDED_URI
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(str(ds_uri))
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
def get_dataset_vs30(vs30: int, dataset_uri: Optional[str] = None) -> ds.Dataset:
    """
    Cache the dataset for a given vs30.

    Args:
      vs30: the VS30 value to partition on.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    ds_uri = dataset_uri or DATASET_AGGR_URI
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(ds_uri)
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
def get_dataset_vs30_nloc0(vs30: int, nloc: str, dataset_uri: Optional[str] = None) -> ds.Dataset:
    """
    Cache the dataset for a given vs30 and nloc_0.

    Args:
      vs30: the VS30 value to partition on.
      nloc: the nloc_0 location code to partition on.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    ds_uri = dataset_uri or DATASET_AGGR_URI
    try:
        source_dir, source_filesystem = pyarrow_dataset.configure_output(ds_uri)
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
