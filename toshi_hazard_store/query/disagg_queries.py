"""Queries for saving and retrieving gridded hazard convenience."""

import logging
from typing import Iterable, Iterator, Union, Type
import decimal

from nzshm_common.location.code_location import CodedLocation
from toshi_hazard_store.model import DisaggAggregationExceedance, DisaggAggregationOccurence, ProbabilityEnum, AggregationEnum
from .hazard_query import downsample_code, get_hashes, have_mixed_length_vs30s
log = logging.getLogger(__name__)


# aliases for models
mDAE = DisaggAggregationExceedance
mDAO = DisaggAggregationOccurence

def get_one_disagg_aggregation(
    location: CodedLocation,
    vs30: float,
    imt: str,
    hazard_agg: AggregationEnum,
    disagg_agg: AggregationEnum,
    poe: ProbabilityEnum,
    hazard_model_id: str,
    model: Type[Union[mDAE, mDAO]] = mDAE
) -> Union[mDAE, mDAO, None]:
    """Fetch model based on single model arguments."""

    """
            f'{self.nloc_001}:{vs30s}:{self.imt}:{self.hazard_agg}:{self.disagg_agg}:'
            f'{self.probability.name}:{self.hazard_model_id}'
    """

    # # model: Union[mDAE, mDAO, None] = None
    # if is_exceedance:
    #     model = mDAE
    # else:
    #     model = mDAO
    qry = model.query(
        downsample_code(location, 0.1),
        model.sort_key == f'{location}:{vs30}:{imt}:{hazard_agg.value}:{disagg_agg.value}:{poe.name}:{hazard_model_id}')
    log.warning(f"get_one_disagg_aggregation: qry {qry}")
    result = list(qry)
    assert len(result) in [0, 1]
    if len(result):
        return result[0]
    return None

def get_disagg_aggregates(
    locs: Iterable[CodedLocation],  # nloc_001
    vs30s: Iterable[float],
    imts: Iterable[str],
    hazard_aggs: Iterable[AggregationEnum],
    disagg_aggs: Iterable[AggregationEnum],
    poes: Iterable[ProbabilityEnum],
    hazard_model_ids: Iterable[str],
    model: Type[Union[mDAE, mDAO]] = mDAE
    ) -> Iterator[Union[mDAE, mDAO]]:
    #     """Fetch models based on criteria."""
    # if is_exceedance:
    #     model = mDAE
    # else:
    #     model = mDAO

    hazard_agg_keys = [a.value for a in hazard_aggs]
    disagg_agg_keys = [a.value for a in disagg_aggs]
    poe_keys = [a for a in poes]

    # print(poe_keys[0])

    def build_sort_key(locs, vs30s, imts, hazard_agg_keys, disagg_agg_keys, poe_keys, hazard_model_ids):
        """Build sort_key."""

        sort_key = ""
        sort_key = sort_key + f":{sorted(locs)[0]}" if locs else sort_key
        sort_key = sort_key + f":{sorted(vs30s)[0]}" if locs and vs30s else sort_key
        if have_mixed_length_vs30s(vs30s):  # we must stop the sort_key build here
                return sort_key
        sort_key = sort_key + f":{sorted(imts)[0]}" if locs and vs30s and imts else sort_key
        sort_key = sort_key + f":{sorted(hazard_agg_keys)[0]}" if locs and vs30s and imts and hazard_agg_keys else sort_key
        sort_key = sort_key + f":{sorted(disagg_agg_keys)[0]}" if locs and vs30s and imts and hazard_agg_keys and disagg_agg_keys else sort_key
        sort_key = sort_key + f":{sorted([p.name for p in poe_keys])[0]}" if locs and vs30s and imts and hazard_agg_keys and disagg_agg_keys and poe_keys else sort_key
        sort_key = sort_key + f":{sorted([_id for _id in hazard_model_ids])[0]}" if locs and vs30s and imts and hazard_agg_keys and disagg_agg_keys and poe_keys and hazard_model_ids else sort_key
        return sort_key

    def build_condition_expr(locs, vs30s, imts, hazard_agg_keys, disagg_agg_keys, poe_keys, hazard_model_ids):
        """Build filter condition."""
        ## TODO REFACTOR ME ... using the res of first loc is not ideal
        grid_res = decimal.Decimal(str(list(locs)[0].split('~')[0]))
        places = grid_res.as_tuple().exponent
        res = float(decimal.Decimal(10) ** places)
        locs = [downsample_code(loc, res) for loc in locs]

        condition_expr = None

        if places == -1:
            condition_expr = condition_expr & model.nloc_1.is_in(*locs)
        if places == -2:
            condition_expr = condition_expr & model.nloc_01.is_in(*locs)
        if places == -3:
            condition_expr = condition_expr & model.nloc_001.is_in(*locs)

        if vs30s:
            condition_expr = condition_expr & model.vs30.is_in(*vs30s)
        if imts:
            condition_expr = condition_expr & model.imt.is_in(*imts)
        if hazard_aggs:
            condition_expr = condition_expr & model.hazard_agg.is_in(*hazard_agg_keys)
        if disagg_aggs:
            condition_expr = condition_expr & model.disagg_agg.is_in(*disagg_agg_keys)
        if poe_keys:
            condition_expr = condition_expr & model.probability.is_in(*poe_keys)
        if hazard_model_ids:
            condition_expr = condition_expr & model.hazard_model_id.is_in(*hazard_model_ids)

        log.info(f'query condition {condition_expr}')
        return condition_expr

    # TODO: this can be parallelised/optimised.
    for hash_location_code in get_hashes(locs):

        log.info('hash_key %s' % hash_location_code)

        hash_locs = list(filter(lambda loc: downsample_code(loc, 0.1) == hash_location_code, locs))
        sort_key_first_val = build_sort_key(hash_locs, vs30s, imts, hazard_agg_keys, disagg_agg_keys, poe_keys, hazard_model_ids)
        condition_expr = build_condition_expr(hash_locs, vs30s, imts, hazard_agg_keys, disagg_agg_keys, poe_keys, hazard_model_ids)

        log.info(f'model {model}')
        log.info(f'hash_location_code {hash_location_code}')
        log.info(f'sort_key_first_val {sort_key_first_val}')
        log.info(f'condition_expr {condition_expr}')

        if sort_key_first_val:
            qry = model.query(
                hash_location_code,
                model.sort_key >= sort_key_first_val,
                filter_condition=condition_expr)
        else:
            qry = model.query(
                hash_location_code,
                model.sort_key >= " ",  # lowest printable char in ascii table is SPACE. (NULL is first control)
                filter_condition=condition_expr,
            )

        log.info(f"get_disagg_aggregates: qry {qry}")

        for hit in qry:
            yield hit
