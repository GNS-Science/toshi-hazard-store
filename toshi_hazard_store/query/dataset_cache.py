"""Dataset caching functionality for hazard queries."""

import datetime as dt
import logging
from functools import lru_cache
from typing import Optional

import pyarrow as pa
import pyarrow.dataset as ds

from toshi_hazard_store.config import DATASET_AGGR_URI, DATASET_DISAGG_AGGR_URI, DATASET_GRIDDED_URI
from toshi_hazard_store.model.gridded.gridded_hazard_pydantic import GriddedHazardPoeLevels
from toshi_hazard_store.model.hazard_models_pydantic import DisaggregationAggregate, HazardAggregateCurve
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.query.hazard_query import downsample_code

log = logging.getLogger(__name__)

GB = 1024**3


def _plain_schema(schema: pa.Schema) -> pa.Schema:
    """Return a copy of schema with all dictionary-encoded fields replaced by their value type.

    Hive partition values are read as plain strings from the path, so pyarrow cannot match
    them to dictionary fields unless the dictionary is pre-populated. Stripping the encoding
    here lets ds.dataset() discover and open the dataset correctly; parquet files are still
    read with their native dictionary encoding.
    """
    return pa.schema(
        [pa.field(f.name, f.type.value_type if pa.types.is_dictionary(f.type) else f.type) for f in schema]
    )


def _open_partitioned_dataset(base_uri: str, schema: pa.Schema, parts: list[tuple[str, str]]) -> ds.Dataset:
    """Open a hive-partitioned parquet dataset at <base_uri>/{k}={v}/{k}={v}/...

    Wraps ds.dataset() in a try/except that raises RuntimeError with the substring
    'Failed to open dataset' so the query wrapper's deferred-warning pattern matches.
    """
    start_time = dt.datetime.now()
    source_dir, source_filesystem = pyarrow_dataset.configure_output(base_uri)
    suffix = "/".join(f"{k}={v}" for k, v in parts)
    dspath = f"{source_dir}/{suffix}" if suffix else source_dir
    log.debug(f"Opening dataset at `{dspath}`")
    try:
        dataset = ds.dataset(
            dspath,
            filesystem=source_filesystem,
            partitioning="hive",
            format="parquet",
            schema=_plain_schema(schema),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:
        raise RuntimeError(f"Failed to open dataset: {e}")
    return dataset


# ---------------------------------------------------------------------------
# Hazard aggregate curve accessors
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_dataset(dataset_uri: Optional[str] = None) -> ds.Dataset:
    """
    Cache the dataset.

    Args:
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    return _open_partitioned_dataset(
        dataset_uri or DATASET_AGGR_URI,
        HazardAggregateCurve.pyarrow_schema(),
        [],
    )


@lru_cache(maxsize=1)
def get_gridded_dataset(dataset_uri: Optional[str] = None) -> ds.Dataset:
    ds_uri = dataset_uri or DATASET_GRIDDED_URI
    return _open_partitioned_dataset(
        str(ds_uri),
        GriddedHazardPoeLevels.pyarrow_schema(),
        [],
    )


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
    return _open_partitioned_dataset(
        dataset_uri or DATASET_AGGR_URI,
        HazardAggregateCurve.pyarrow_schema(),
        [("vs30", str(vs30))],
    )


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
    return _open_partitioned_dataset(
        dataset_uri or DATASET_AGGR_URI,
        HazardAggregateCurve.pyarrow_schema(),
        [("vs30", str(vs30)), ("nloc_0", downsample_code(nloc, 1.0))],
    )


# ---------------------------------------------------------------------------
# Disaggregation aggregate accessors
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_disagg_aggr_dataset(dataset_uri: Optional[str] = None) -> ds.Dataset:
    """
    Cache the disaggregation aggregate dataset.

    Args:
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_DISAGG_AGGR_URI env var.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    return _open_partitioned_dataset(
        dataset_uri or DATASET_DISAGG_AGGR_URI,
        DisaggregationAggregate.pyarrow_schema(),
        [],
    )


@lru_cache(maxsize=3)
def get_disagg_aggr_dataset_digest_vs30(
    bins_digest: str, vs30: int, dataset_uri: Optional[str] = None
) -> ds.Dataset:
    """
    Cache the disaggregation aggregate dataset for a given bins_digest and vs30.

    Args:
      bins_digest: the bins compatibility digest to partition on.
      vs30: the VS30 value to partition on.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_DISAGG_AGGR_URI env var.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    return _open_partitioned_dataset(
        dataset_uri or DATASET_DISAGG_AGGR_URI,
        DisaggregationAggregate.pyarrow_schema(),
        [("bins_digest", bins_digest), ("vs30", str(vs30))],
    )


@lru_cache(maxsize=32)
def get_disagg_aggr_dataset_digest_vs30_nloc0(
    bins_digest: str, vs30: int, nloc: str, dataset_uri: Optional[str] = None
) -> ds.Dataset:
    """
    Cache the disaggregation aggregate dataset for a given bins_digest, vs30, and nloc_0.

    Args:
      bins_digest: the bins compatibility digest to partition on.
      vs30: the VS30 value to partition on.
      nloc: the nloc_0 location code to partition on.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_DISAGG_AGGR_URI env var.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    return _open_partitioned_dataset(
        dataset_uri or DATASET_DISAGG_AGGR_URI,
        DisaggregationAggregate.pyarrow_schema(),
        [("bins_digest", bins_digest), ("vs30", str(vs30)), ("nloc_0", downsample_code(nloc, 1.0))],
    )
