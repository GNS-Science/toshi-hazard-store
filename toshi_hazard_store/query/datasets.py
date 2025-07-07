"""query interfaces for pyarrow datasets

Datasets objects are cached to reduce overhead in future queries.

https://arrow.apache.org/docs/python/parquet.html#reading-and-writing-the-apache-parquet-format

"""

import datetime as dt
import itertools
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Union

import pyarrow.compute as pc
import pyarrow.dataset as ds

from toshi_hazard_store.config import DATASET_AGGR_URI
from toshi_hazard_store.model.pyarrow.dataset_schema import get_hazard_aggregate_schema
from toshi_hazard_store.query.hazard_query import downsample_code, get_hashes

log = logging.getLogger(__name__)

IMT_44_LVLS = [
    0.0001,
    0.0002,
    0.0004,
    0.0006,
    0.0008,
    0.001,
    0.002,
    0.004,
    0.006,
    0.008,
    0.01,
    0.02,
    0.04,
    0.06,
    0.08,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
    1.2,
    1.4,
    1.6,
    1.8,
    2.0,
    2.2,
    2.4,
    2.6,
    2.8,
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
    6.0,
    7.0,
    8.0,
    9.0,
    10.0,
]


@dataclass
class IMTValue:
    """Represents an intensity measure type (IMT) value.

    Attributes:
        lvl: The level of the IMT value.
        val: The value of the IMT at that level.
    """

    lvl: float  # noqa: F821
    val: float  # noqa: F821


@dataclass
class AggregatedHazard:
    """
    Represents an aggregated hazard dataset.

    Attributes:
        compatible_calc_id (str): the ID of a compatible calculation for PSHA engines interoperability.
        hazard_model_id (str): the model that these curves represent.
        nloc_001 (str): the location string to three places e.g. "-38.330~17.550".
        nloc_0 (str): the location string to zero places e.g.  "-38.0~17.0" (used for partitioning).
        imt (str): the intensity measure type label e.g. 'PGA', 'SA(5.0)'.
        vs30 (int): the VS30 integer.
        agg (str): the aggregation type.
        values (list[Union[float, IMTValue]]): a list of 44 IMTL values.

    Notes:
        This class is designed to match the table schema for aggregated hazard datasets.
    """

    compatable_calc_id: str
    hazard_model_id: str
    nloc_001: str
    nloc_0: str
    imt: str
    vs30: int
    agg: str
    values: list[Union[float, 'IMTValue']]

    def to_imt_values(self):
        """
        Converts the IMTL values in this object's `values` attribute from a list of floats to a list of `IMTValue`
        objects.
        Returns:
            AggregatedHazard: this object itself.
        """
        new_values = zip(IMT_44_LVLS, self.values)
        self.values = [IMTValue(*x) for x in new_values]
        return self


@lru_cache()
def get_dataset() -> ds.Dataset:
    """
    Cache the dataset.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    try:
        dataset = ds.dataset(
            DATASET_AGGR_URI, partitioning='hive', format='parquet', schema=get_hazard_aggregate_schema()
        )
        log.info(f"Opened dataset `{DATASET_AGGR_URI}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset {DATASET_AGGR_URI}: {e}")
    return dataset


@lru_cache()
def get_dataset_vs30(vs30: int) -> ds.Dataset:
    """
    Cache the dataset for a given vs30.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    try:
        dspath = f"{DATASET_AGGR_URI}/vs30={vs30}"
        dataset = ds.dataset(dspath, partitioning='hive', format='parquet', schema=get_hazard_aggregate_schema())
        log.info(f"Opened dataset `{dspath}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset {dspath}: {e}")
    return dataset


@lru_cache()
def get_dataset_vs30_nloc0(vs30: int, nloc: str) -> ds.Dataset:
    """
    Cache the dataset for a given vs30 and nloc_0.

    Returns:
      A pyarrow.dataset.Dataset object.
    """
    start_time = dt.datetime.now()
    try:
        dspath = f"{DATASET_AGGR_URI}/vs30={vs30}/nloc_0={downsample_code(nloc, 1.0)}"
        dataset = ds.dataset(dspath, partitioning='hive', format='parquet', schema=get_hazard_aggregate_schema())
        log.info(f"Opened dataset `{dspath}` in {dt.datetime.now() - start_time}.")
    except Exception as e: # pragma: no cover
        raise RuntimeError(f"Failed to open dataset {dspath}: {e}")
    return dataset


def get_hazard_curves_naive(location_codes, vs30s, hazard_model, imts, aggs):
    """
    Retrieves aggregated hazard curves from the dataset.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model (list): List of hazard model IDs.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.
    """
    log.debug('> get_hazard_curves()')
    t0 = dt.datetime.now()

    dataset = get_dataset()
    flt = (
        (pc.field('aggr').isin(aggs))
        & (pc.field("nloc_0").isin(get_hashes(location_codes, resolution=1)))
        & (pc.field("nloc_001").isin(location_codes))
        & (pc.field("imt").isin(imts))
        & (pc.field("vs30").isin(vs30s))
        & (pc.field('hazard_model_id') == hazard_model)
    )
    table = dataset.to_table(filter=flt)

    t1 = dt.datetime.now()
    log.debug(f"to_table for filter took {(t1 - t0).total_seconds()} seconds.")
    log.debug(f"schema {table.schema}")

    count = 0
    for batch in table.to_batches():  # pragma: no branch
        for row in zip(*batch.columns):  # pragma: no branch
            count += 1
            item = (x.as_py() for x in row)
            obj = AggregatedHazard(*item).to_imt_values()
            if obj.vs30 not in vs30s:
                raise RuntimeError(f"vs30 {obj.vs30} not in {vs30s}. Is schema correct?")  # pragma: no cover
            yield obj

    t1 = dt.datetime.now()  # pragma: no cover
    log.info(f"Executed dataset query for {count} curves in {(t1 - t0).total_seconds()} seconds.")


def get_hazard_curves_by_vs30(location_codes, vs30s, hazard_model, imts, aggs):
    """
    Retrieves aggregated hazard curves from the dataset.

    Subdivides the dataset using partitioning to reduce IO and memory demand.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model (list): List of hazard model IDs.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.
    """
    log.debug('> get_hazard_curves()')
    t0 = dt.datetime.now()

    for vs30 in vs30s:  # pragma: no branch

        dataset = get_dataset_vs30(vs30)

        flt = (
            (pc.field('aggr').isin(aggs))
            & (pc.field("nloc_0").isin(get_hashes(location_codes, resolution=1)))
            & (pc.field("nloc_001").isin(location_codes))
            & (pc.field("imt").isin(imts))
            & (pc.field('hazard_model_id') == hazard_model)
        )

        table = dataset.to_table(filter=flt)
        t1 = dt.datetime.now()
        log.debug(f"to_table for filter took {(t1 - t0).total_seconds()} seconds.")
        log.debug(f"schema {table.schema}")

        count = 0
        for batch in table.to_batches():  # pragma: no branch
            for row in zip(*batch.columns):  # pragma: no branch
                count += 1
                item = (x.as_py() for x in row)
                obj = AggregatedHazard(*item).to_imt_values()
                obj.vs30 = vs30
                if obj.imt not in imts:
                    raise RuntimeError(f"imt {obj.imt} not in {imts}. Is schema correct?")  # pragma: no cover
                yield obj

        t1 = dt.datetime.now()  # pragma: no cover
        log.info(f"Executed dataset query for {count} curves in {(t1 - t0).total_seconds()} seconds.")


def get_hazard_curves_by_vs30_nloc0(location_codes, vs30s, hazard_model, imts, aggs):
    """
    Retrieves aggregated hazard curves from the dataset.

    Subdivides the dataset using partitioning to reduce IO and memory demand.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model (list): List of hazard model IDs.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.
    """
    log.debug('> get_hazard_curves()')
    t0 = dt.datetime.now()

    for hash_location_code in get_hashes(location_codes, 1):

        log.debug('hash_key %s' % hash_location_code)
        hash_locs = list(filter(lambda loc: downsample_code(loc, 1) == hash_location_code, location_codes))

        for hloc, vs30 in itertools.product(hash_locs, vs30s):

            dataset = get_dataset_vs30_nloc0(vs30, hloc)
            t1 = dt.datetime.now()
            flt = (
                (pc.field('aggr').isin(aggs))
                & (pc.field("nloc_001").isin(hash_locs))
                & (pc.field("imt").isin(imts))
                & (pc.field('hazard_model_id') == hazard_model)
            )

            table = dataset.to_table(filter=flt)
            t2 = dt.datetime.now()
            log.debug(f"to_table for filter took {(t2 - t1).total_seconds()} seconds.")
            log.debug(f"schema {table.schema}")

            count = 0
            for batch in table.to_batches():  # pragma: no branch
                for row in zip(*batch.columns):  # pragma: no branch
                    count += 1
                    item = (x.as_py() for x in row)
                    obj = AggregatedHazard(*item).to_imt_values()
                    obj.vs30 = vs30
                    obj.nloc_0 = hloc
                    if obj.imt not in imts:
                        raise RuntimeError(f"imt {obj.imt} not in {imts}. Is schema correct?")  # pragma: no cover 
                    yield obj

        t3 = dt.datetime.now()  # pragma: no cover
        log.info(f"Executed dataset query for {count} curves in {(t3 - t0).total_seconds()} seconds.")
