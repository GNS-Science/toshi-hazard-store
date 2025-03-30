import json
import logging
import math
import random
from dataclasses import dataclass

import pandas as pd

from toshi_hazard_store.model import openquake_models
from toshi_hazard_store.transform import parse_logic_tree_branches

log = logging.getLogger(__name__)

BATCH_SIZE = random.randint(15, 50)


@dataclass
class OpenquakeMeta:
    source_lt: pd.DataFrame
    gsim_lt: pd.DataFrame
    rlz_lt: pd.DataFrame
    model: openquake_models.ToshiOpenquakeMeta


def export_meta_v3(extractor, toshi_hazard_id, toshi_gt_id, locations_id, source_tags, source_ids):
    """Extract and same the meta data."""
    oq = json.loads(extractor.get('oqparam').json)
    source_lt, gsim_lt, rlz_lt = parse_logic_tree_branches(extractor)

    df_len = 0
    df_len += len(source_lt.to_json())
    df_len += len(gsim_lt.to_json())
    df_len += len(rlz_lt.to_json())

    if df_len >= 300e3:
        log.warning('WARNING: Dataframes for this job may be too large to store on DynamoDB.')

    vs30 = oq['reference_vs30_value']

    if math.isnan(vs30):
        vs30 = 0

    log.debug(f'vs30: {vs30}')

    obj = openquake_models.ToshiOpenquakeMeta(
        partition_key="ToshiOpenquakeMeta",
        hazard_solution_id=toshi_hazard_id,
        general_task_id=toshi_gt_id,
        hazsol_vs30_rk=f"{toshi_hazard_id}:{str(int(vs30)).zfill(3)}",
        # updated=dt.datetime.now(tzutc()),
        # known at configuration
        vs30=int(vs30),  # vs30 value
        imts=list(oq['hazard_imtls'].keys()),  # list of IMTs
        locations_id=locations_id,  # Location code or list ID
        source_tags=source_tags,
        source_ids=source_ids,
        inv_time=oq['investigation_time'],
        src_lt=source_lt.to_json(),  # sources meta as DataFrame JSON
        gsim_lt=gsim_lt.to_json(),  # gmpe meta as DataFrame JSON
        rlz_lt=rlz_lt.to_json(),  # realization meta as DataFrame JSON
    )
    obj.save()
    return OpenquakeMeta(source_lt, gsim_lt, rlz_lt, obj)
