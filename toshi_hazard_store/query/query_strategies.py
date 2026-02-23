"""Different query strategies for hazard curve retrieval."""

import datetime as dt
import itertools
import logging
from typing import Iterator, Optional

import pyarrow.compute as pc

from toshi_hazard_store.query.dataset_cache import get_dataset, get_dataset_vs30, get_dataset_vs30_nloc0
from toshi_hazard_store.query.hazard_query import downsample_code, get_hashes
from toshi_hazard_store.query.models import AggregatedHazard

log = logging.getLogger(__name__)


def get_hazard_curves_naive(
    location_codes: list[str],
    vs30s: list[int],
    hazard_model: str,
    imts: list[str],
    aggs: list[str],
    dataset_uri: Optional[str] = None,
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.
    """
    log.debug(f"> get_hazard_curves_naive() location_codes: {location_codes}")
    t0 = dt.datetime.now()

    dataset = get_dataset(dataset_uri)
    nloc_001_locs = [downsample_code(loc, 0.001) for loc in location_codes]
    flt = (
        (pc.field("aggr").isin(aggs))
        & (pc.field("nloc_0").isin(get_hashes(location_codes, resolution=1)))
        & (pc.field("nloc_001").isin(nloc_001_locs))
        & (pc.field("imt").isin(imts))
        & (pc.field("vs30").isin(vs30s))
        & (pc.field("hazard_model_id") == hazard_model)
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
            # log.info(f'row: {row}')
            item = (x.as_py() for x in row)
            # log.info(f'item: {item}')
            obj = AggregatedHazard(*item).to_imt_values()
            if obj.vs30 not in vs30s:
                raise RuntimeError(f"vs30 {obj.vs30} not in {vs30s}. Is schema correct?")  # pragma: no cover
            yield obj

    t1 = dt.datetime.now()  # pragma: no cover
    log.debug(f"Executed dataset query for {count} curves in {(t1 - t0).total_seconds()} seconds.")


def get_hazard_curves_by_vs30(
    location_codes: list[str],
    vs30s: list[int],
    hazard_model: str,
    imts: list[str],
    aggs: list[str],
    dataset_uri: Optional[str] = None,
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    Subdivides the dataset using vs30 partitioning to reduce IO and memory demand.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.

    Raises:
      RuntimeWarning: describing any dataset partitions that could not be opened.
    """
    log.debug(f"> get_hazard_curves_by_vs30({location_codes}, {vs30s},...)")
    t0 = dt.datetime.now()

    dataset_exceptions = []

    nloc_001_locs = [downsample_code(loc, 0.001) for loc in location_codes]
    for vs30 in vs30s:  # pragma: no branch
        count = 0
        try:
            dataset = get_dataset_vs30(vs30, dataset_uri)
        except Exception:
            dataset_exceptions.append(f"Failed to open dataset for vs30={vs30}")
            continue

        flt = (
            (pc.field("aggr").isin(aggs))
            & (pc.field("nloc_0").isin(get_hashes(location_codes, resolution=1)))
            & (pc.field("nloc_001").isin(nloc_001_locs))
            & (pc.field("imt").isin(imts))
            & (pc.field("hazard_model_id") == hazard_model)
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
    location_codes: list[str],
    vs30s: list[int],
    hazard_model: str,
    imts: list[str],
    aggs: list[str],
    dataset_uri: Optional[str] = None,
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    Subdivides the dataset using vs30 and nloc_0 partitioning to reduce IO and memory demand.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.

    Raises:
      RuntimeWarning: describing any dataset partitions that could not be opened.
    """
    log.debug(f"> get_hazard_curves_by_vs30_nloc0({location_codes}, {vs30s},...)")
    t0 = dt.datetime.now()

    dataset_exceptions = []

    for hash_location_code in get_hashes(location_codes, 1):
        log.debug("hash_key %s" % hash_location_code)
        hash_locs = list(
            filter(
                lambda loc: downsample_code(loc, 1) == hash_location_code,
                location_codes,
            )
        )
        nloc_001_locs = [downsample_code(loc, 0.001) for loc in hash_locs]

        count = 0

        for hloc, vs30 in itertools.product(hash_locs, vs30s):
            try:
                dataset = get_dataset_vs30_nloc0(vs30, hloc, dataset_uri)
            except Exception as exc:
                dataset_exceptions.append(str(exc))
                continue

            t1 = dt.datetime.now()
            flt = (
                (pc.field("aggr").isin(aggs))
                & (pc.field("nloc_001").isin(nloc_001_locs))
                & (pc.field("imt").isin(imts))
                & (pc.field("hazard_model_id") == hazard_model)
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
