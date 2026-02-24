"""Main query interface for hazard datasets."""

import datetime as dt
import logging
from typing import Iterator, Optional

import pyarrow.compute as pc

from toshi_hazard_store.model.gridded.gridded_hazard_pydantic import GriddedHazardPoeLevels
from toshi_hazard_store.query.dataset_cache import get_gridded_dataset
from toshi_hazard_store.query.models import AggregatedHazard
from toshi_hazard_store.query.query_strategies import (
    get_hazard_curves_by_vs30,
    get_hazard_curves_by_vs30_nloc0,
    get_hazard_curves_naive,
)

log = logging.getLogger(__name__)


def get_hazard_curves(
    location_codes: list[str],
    vs30s: list[int],
    hazard_model: str,
    imts: list[str],
    aggs: list[str],
    strategy: str = "naive",
    dataset_uri: Optional[str] = None,
) -> Iterator[AggregatedHazard]:
    """
    Retrieves aggregated hazard curves from the dataset.

    The optional `strategy` argument can be used to control how the query behaves:
     - 'naive' (the default) lets pyarrow do its normal thing.
     - 'd1' assumes the dataset is partitioned on `vs30`, generating multiple pyarrow queries from the user args.
     - 'd2' assumes the dataset is partitioned on `vs30, nloc_0` and acts accordingly.

    These overriding strategies allow the user to tune the query to suit the size of the datasets and the
    compute resources available. e.g. for the full NSHM, with an AWS lambda function, the `d2` option is optimal.

    Args:
      location_codes (list): List of location codes.
      vs30s (list): List of VS30 values.
      hazard_model: the hazard model id.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.
      strategy: which query strategy to use (options are `d1`, `d2`, `naive`).
          Other values will use the `naive` strategy.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_AGGR_URI env var.

    Yields:
      AggregatedHazard: An object containing the aggregated hazard curve data.
    Raises:
      RuntimeWarning: describing any dataset partitions that could not be opened.
    """
    log.debug("> get_hazard_curves()")
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
        for obj in qfn(location_codes, vs30s, hazard_model, imts, aggs, dataset_uri):  # pragma: no branch
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


def get_gridded_hazard(
    location_grid_id: str,
    hazard_model_ids: list[str],
    vs30s: list[float],
    imts: list[str],
    aggs: list[str],
    poes: list[float],
    dataset_uri: Optional[str] = None,
) -> Iterator[GriddedHazardPoeLevels]:
    """
    Retrieves gridded hazard from the parquet dataset.

    Args:
      location_grid_id: the grid identifier to query.
      hazard_model_ids (list): List of hazard model identifiers.
      vs30s (list): List of VS30 values.
      imts (list): List of intensity measure types (e.g. 'PGA', 'SA(5.0)').
      aggs (list): List of aggregation types.
      poes (list): List of probability of exceedance values.
      dataset_uri: optional URI for the dataset. Defaults to the THS_DATASET_GRIDDED_URI env var.

    Yields:
      GriddedHazardPoeLevels: An object containing the gridded hazard data.
    """

    log.debug("> get_gridded_hazard")
    t0 = dt.datetime.now()

    gridded_dataset = get_gridded_dataset(dataset_uri)
    flt = (
        (pc.field("location_grid_id") == location_grid_id)
        & (pc.field("aggr").isin(aggs))
        & (pc.field("imt").isin(imts))
        & (pc.field("vs30").isin(vs30s))
        & (pc.field("poe").isin(poes))
        & (pc.field("hazard_model_id").isin(hazard_model_ids))
    )

    log.debug(f"filter: {flt}")
    table = gridded_dataset.to_table(filter=flt)

    t1 = dt.datetime.now()
    log.debug(f"to_table for filter took {(t1 - t0).total_seconds()} seconds.")
    log.debug(f"schema {table.schema}")

    # NB the following emulates the method used in AggregatedHazard, but it's significantly slower than
    # below using pa.Table.to_pandas()
    # column_names = table.schema.names
    # for batch in table.to_batches():  # pragma: no branch
    #     for row in zip(*batch.columns):  # pragma: no branch
    #         # count += 1
    #         # print(row)
    #         vals = (x.as_py() for x in row)
    #         item = {x[0]:x[1] for x in zip(column_names, vals)}
    #         obj = GriddedHazardPoeLevels.model_construct(**item)
    #         yield obj

    df0 = table.to_pandas()
    for row_dict in df0.to_dict(orient="records"):
        # yield GriddedHazardPoeLevels(**row_dict) # SLOW because of the expensive validators on
        # this Pydantic Model class.
        yield GriddedHazardPoeLevels.model_construct(**row_dict)  # FAST
