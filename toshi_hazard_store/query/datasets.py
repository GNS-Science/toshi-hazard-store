"""query interfaces for pyarrow datasets

Datasets objects are cached to reduce overhead in future queries.

https://arrow.apache.org/docs/python/parquet.html#reading-and-writing-the-apache-parquet-format

"""

import datetime as dt
import itertools
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator, Union

import pyarrow.compute as pc
import pyarrow.dataset as ds

from toshi_hazard_store.config import DATASET_AGGR_URI
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
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
        source_dir, source_filesystem = pyarrow_dataset.configure_output(DATASET_AGGR_URI)
        dataset = ds.dataset(
            source_dir,
            filesystem=source_filesystem,
            partitioning='hive',
            format='parquet',
            schema=get_hazard_aggregate_schema(),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset: {e}")
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
        source_dir, source_filesystem = pyarrow_dataset.configure_output(DATASET_AGGR_URI)
        dspath = f"{source_dir}/vs30={vs30}"
        dataset = ds.dataset(
            dspath,
            filesystem=source_filesystem,
            partitioning='hive',
            format='parquet',
            schema=get_hazard_aggregate_schema(),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset: {e}")
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
        source_dir, source_filesystem = pyarrow_dataset.configure_output(DATASET_AGGR_URI)
        log.debug(f"source_dir:`{source_dir}`, filesystem: `{source_filesystem}`")
        dspath = f"{source_dir}/vs30={vs30}/nloc_0={downsample_code(nloc, 1.0)}"
        log.debug(f"Opening dspath :`{dspath}`")
        dataset = ds.dataset(
            dspath,
            filesystem=source_filesystem,
            partitioning='hive',
            format='parquet',
            schema=get_hazard_aggregate_schema(),
        )
        log.info(f"Opened dataset `{dataset}` in {dt.datetime.now() - start_time}.")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to open dataset: {e}")
    return dataset


def get_hazard_curves_naive(
    location_codes: list[str], vs30s: list[int], hazard_model: str, imts: list[str], aggs: list[str]
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.
    """
    log.debug('> get_hazard_curves_naive()')
    t0 = dt.datetime.now()

    dataset = get_dataset()
    nloc_001_locs = [downsample_code(loc, 0.001) for loc in location_codes]
    flt = (
        (pc.field('aggr').isin(aggs))
        & (pc.field("nloc_0").isin(get_hashes(location_codes, resolution=1)))
        & (pc.field("nloc_001").isin(nloc_001_locs))
        & (pc.field("imt").isin(imts))
        & (pc.field("vs30").isin(vs30s))
        & (pc.field('hazard_model_id') == hazard_model)
    )
    log.debug(f"filter: {flt}")
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
    log.debug(f"Executed dataset query for {count} curves in {(t1 - t0).total_seconds()} seconds.")


def get_hazard_curves_by_vs30(
    location_codes: list[str], vs30s: list[int], hazard_model: str, imts: list[str], aggs: list[str]
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    Subdivides the dataset using partitioning to reduce IO and memory demand.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.

    Raises:
      RuntimeWarning: describing any dataset partitions that could not be opened.
    """
    log.debug(f'> get_hazard_curves_by_vs30({location_codes}, {vs30s},...)')
    t0 = dt.datetime.now()

    dataset_exceptions = []

    nloc_001_locs = [downsample_code(loc, 0.001) for loc in location_codes]
    for vs30 in vs30s:  # pragma: no branch

        count = 0
        try:
            dataset = get_dataset_vs30(vs30)
        except Exception:
            dataset_exceptions.append(f"Failed to open dataset for vs30={vs30}")
            continue

        flt = (
            (pc.field('aggr').isin(aggs))
            & (pc.field("nloc_0").isin(get_hashes(location_codes, resolution=1)))
            & (pc.field("nloc_001").isin(nloc_001_locs))
            & (pc.field("imt").isin(imts))
            & (pc.field('hazard_model_id') == hazard_model)
        )
        log.debug(f"filter: {flt}")
        table = dataset.to_table(filter=flt)
        t1 = dt.datetime.now()
        log.debug(f"to_table for filter took {(t1 - t0).total_seconds()} seconds.")
        log.debug(f"schema {table.schema}")

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
        log.debug(f"Executed dataset query for {count} curves in {(t1 - t0).total_seconds()} seconds.")

    if dataset_exceptions:  # pragma: no branch
        raise RuntimeWarning(f"Dataset errors: {dataset_exceptions}")


def get_hazard_curves_by_vs30_nloc0(
    location_codes: list[str], vs30s: list[int], hazard_model: str, imts: list[str], aggs: list[str]
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    Subdivides the dataset using partitioning to reduce IO and memory demand.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.

    Raises:
      RuntimeWarning: describing any dataset partitions that could not be opened.
    """
    log.debug(f'> get_hazard_curves_by_vs30_nloc0({location_codes}, {vs30s},...)')
    t0 = dt.datetime.now()

    dataset_exceptions = []

    for hash_location_code in get_hashes(location_codes, 1):
        log.debug('hash_key %s' % hash_location_code)
        hash_locs = list(filter(lambda loc: downsample_code(loc, 1) == hash_location_code, location_codes))
        nloc_001_locs = [downsample_code(loc, 0.001) for loc in hash_locs]

        count = 0

        for hloc, vs30 in itertools.product(hash_locs, vs30s):

            try:
                dataset = get_dataset_vs30_nloc0(vs30, hloc)
            except Exception as exc:
                dataset_exceptions.append(str(exc))
                continue

            t1 = dt.datetime.now()
            flt = (
                (pc.field('aggr').isin(aggs))
                & (pc.field("nloc_001").isin(nloc_001_locs))
                & (pc.field("imt").isin(imts))
                & (pc.field('hazard_model_id') == hazard_model)
            )
            log.debug(f"filter: {flt}")
            table = dataset.to_table(filter=flt)
            t2 = dt.datetime.now()
            log.debug(f"to_table for filter took {(t2 - t1).total_seconds()} seconds.")
            log.debug(f"schema {table.schema}")

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
        log.debug(f"Executed dataset query for {count} curves in {(t3 - t0).total_seconds()} seconds.")

    if dataset_exceptions:  # pragma: no branch
        raise RuntimeWarning(f"Dataset errors: {dataset_exceptions}")


def get_hazard_curves(
    location_codes: list[str],
    vs30s: list[int],
    hazard_model: str,
    imts: list[str],
    aggs: list[str],
    strategy: str = 'naive',
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    The optional `strategy` argument can be used to control how the query behaves:
     - 'naive' (the default) lets pyarrow do its normal thing.
     - 'd1' assumes the dataset is partitioned on `vs30`, generating multiple pyarrow queries from the user args.
     - 'd2' assumes the dataset is partitioned on `vs30, nloc_0` and acts accordingly.

    These overriding  strategies alow the user to tune the query to suit the size of the datasets and the
    compute resources available. e.g. for the full NSHM, with an AWS lambda function, the `d2` option is optimal.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      aggs (list): List of aggregation types.
      strategy: which query strategy to use (options are `d1`, `d2`, `naive`).
          Other values will use the `naive` strategy.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.
    Raises:
      RuntimeWarning: describing any dataset partitions that could not be opened.
    """
    log.debug('> get_hazard_curves()')
    t0 = dt.datetime.now()

    count = 0

    if strategy == "d2":
        qfn = get_hazard_curves_by_vs30_nloc0
    elif strategy == "d1":
        qfn = get_hazard_curves_by_vs30
    else:
        qfn = get_hazard_curves_naive

    deferred_warning = None
    try:
        for obj in qfn(location_codes, vs30s, hazard_model, imts, aggs):  # pragma: no branch
            count += 1
            yield obj
    except RuntimeWarning as err:
        if "Failed to open dataset" in str(err):
            deferred_warning = err
        else:
            raise err  # pragma: no cover

    t1 = dt.datetime.now()
    log.info(f"Executed dataset query for {count} curves in {(t1 - t0).total_seconds()} seconds.")

    if deferred_warning:  # pragma: no cover
        raise deferred_warning
