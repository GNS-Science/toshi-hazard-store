import datetime as dt
import json
import logging
import pathlib
import random
from typing import List, Optional, Tuple, Union

from toshi_hazard_store.config import NUM_BATCH_WORKERS, STORAGE_FOLDER
from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.model.hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig
from toshi_hazard_store.model.revision_4 import hazard_realization_curve
from toshi_hazard_store.multi_batch import save_parallel
from toshi_hazard_store.utils import normalise_site_code

from .parse_oq_realizations import build_rlz_mapper

chc_manager = CompatibleHazardCalculationManager(pathlib.Path(STORAGE_FOLDER))
hpc_manager = HazardCurveProducerConfigManager(pathlib.Path(STORAGE_FOLDER), chc_manager)

log = logging.getLogger(__name__)

BATCH_SIZE = random.randint(15, 50)


def export_rlzs_rev4(
    extractor,
    compatible_calc: CompatibleHazardCalculation,
    producer_config: HazardCurveProducerConfig,
    hazard_calc_id: str,
    vs30: int,
    return_rlz=True,
    update_producer=False,
) -> Union[List[hazard_realization_curve.HazardRealizationCurve], None]:

    # first check the FKs are available
    hpc = hpc_manager.load(producer_config.unique_id)
    assert hpc.compatible_calc_fk == compatible_calc.unique_id

    oq = json.loads(extractor.get('oqparam').json)
    sites = extractor.get('sitecol').to_dframe()
    rlzs = extractor.get('hcurves?kind=rlzs', asdict=True)

    ###########################################################
    # TODO: this code block has merit, but is on hold for now
    #
    # rlz_keys = [k for k in rlzs.keys() if 'rlz-' in k]
    # imtls = oq['hazard_imtls']  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}

    # if not set(producer_config.imts).issuperset(set(imtls.keys())):
    #     if not update_producer:
    #         log.error(f'imts do not align {imtls.keys()} <=> {producer_config.imts}')
    #         raise ValueError('bad IMT configuration')
    #     else:
    #         # update producer
    #         producer_config.imts = list(set(producer_config.imts).union(set(imtls.keys())))
    #         imtl_values = set()
    #         for values in imtls.values():
    #             imtl_values.update(set(values))
    #         producer_config.imt_levels = list(set(producer_config.imt_levels).union(imtl_values))
    #         producer_config.save()
    #         log.debug(f'updated: {producer_config}')
    ###########################################################

    rlz_map = build_rlz_mapper(extractor)

    # source_lt, gsim_lt, rlz_lt = parse_logic_tree_branches(extractor)
    # log.debug('rlz %s' % rlz_lt)
    # log.debug('src %s' % source_lt)
    # log.debug('gsim %s' % gsim_lt)

    # TODO : this assumes keys are in same order as rlzs
    # rlz_branch_paths = rlz_lt['branch_path'].tolist()

    # assert 0

    def generate_models():
        log.info("generating models")
        for i_site in range(len(sites)):
            loc = normalise_site_code((sites.loc[i_site, 'lon'], sites.loc[i_site, 'lat']), True)
            # print(f'loc: {loc}')

            for i_rlz in rlz_map.keys():

                # source_branch, gmm_branch = bp.split('~')

                for i_imt, imt in enumerate(imtls.keys()):
                    values = rlzs[rlz_keys[i_rlz]][i_site][i_imt].tolist()
                    # assert len(values) == len(imtls[imt])
                    if not len(values) == len(producer_config.imt_levels):
                        log.error(
                            f'count of imt_levels: {len(producer_config.imt_levels)}'
                            ' and values: {len(values)} do not align.'
                        )
                        raise ValueError('bad IMT levels configuration')

                    # can check actual levels here too
                    if not update_producer:
                        if not imtls[imt] == producer_config.imt_levels:
                            log.error(
                                f'imt_levels not matched: {len(producer_config.imt_levels)}'
                                ' and values: {len(values)} do not align.'
                            )
                            raise ValueError('bad IMT levels configuration')

                    realization = rlz_map[i_rlz]
                    log.debug(realization)
                    oq_realization = hazard_realization_curve.HazardRealizationCurve(
                        compatible_calc_fk=compatible_calc.foreign_key(),
                        producer_config_fk=producer_config.foreign_key(),
                        calculation_id=hazard_calc_id,
                        values=values,
                        imt=imt,
                        vs30=vs30,
                        source_digests=[realization.sources.hash_digest],
                        gmm_digests=[realization.gmms.hash_digest],
                    )
                    # if oqmeta.model.vs30 == 0:
                    #    oq_realization.site_vs30 = sites.loc[i_site, 'vs30']
                    yield oq_realization.set_location(loc)
            log.debug(f"site {loc} done")

    # used for testing
    if return_rlz:
        return list(generate_models())

    save_parallel("", generate_models(), hazard_realization_curve.HazardRealizationCurve, NUM_BATCH_WORKERS, BATCH_SIZE)
    return None
