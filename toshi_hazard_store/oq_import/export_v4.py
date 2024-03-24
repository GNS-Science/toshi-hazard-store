import json
import logging
import random
import datetime as dt

# from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from toshi_hazard_store.config import NUM_BATCH_WORKERS, USE_SQLITE_ADAPTER
from toshi_hazard_store.model.revision_4 import hazard_models
from toshi_hazard_store.multi_batch import save_parallel
from toshi_hazard_store.transform import parse_logic_tree_branches
from toshi_hazard_store.utils import normalise_site_code

log = logging.getLogger(__name__)

NUM_BATCH_WORKERS = 1 if USE_SQLITE_ADAPTER else NUM_BATCH_WORKERS
BATCH_SIZE = 1000 if USE_SQLITE_ADAPTER else random.randint(15, 50)


def create_producer_config(
    partition_key: str,
    compatible_calc: hazard_models.CompatibleHazardCalculation,
    extractor,
    producer_software: str,
    producer_version_id: str,
    configuration_hash: str,
    tags: Optional[List[str]] = None,
    effective_from: Optional[dt.datetime] = None,
    last_used: Optional[dt.datetime] = None,   
    configuration_data: Optional[str] = "",
    notes: Optional[str] = "",
    dry_run: bool = False,
) -> 'hazard_models.HazardCurveProducerConfig':
    # first check the Foreign Key is OK
    mCHC = hazard_models.CompatibleHazardCalculation

    if next(mCHC.query(compatible_calc.foreign_key()[0], mCHC.uniq_id == compatible_calc.foreign_key()[1])) is None:
        raise ValueError(f'compatible_calc: {compatible_calc.foreign_key()} was not found')

    mHCPC = hazard_models.HazardCurveProducerConfig

    # we use the extractor to load template imts and IMT levels
    if extractor:
        oq = json.loads(extractor.get('oqparam').json)
        imtls = oq['hazard_imtls']  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}

    imts = list(imtls.keys()) if extractor else []
    imt_levels = imtls[imts[0]] if extractor else []

    m = mHCPC(
        partition_key=partition_key,
        compatible_calc_fk=compatible_calc.foreign_key(),
        producer_software=producer_software,
        producer_version_id=producer_version_id,
        tags = tags,
        effective_from = effective_from,
        last_used = last_used,
        configuration_hash=configuration_hash,
        configuration_data=configuration_data,
        imts=imts,
        imt_levels=imt_levels,
        notes=notes,
    )
    m.range_key = f"{producer_software}:{producer_version_id}:{configuration_hash}"
    if not dry_run:
        m.save()
    return m


def get_compatible_calc(foreign_key: Tuple[str, str]):
    try:
        mCHC = hazard_models.CompatibleHazardCalculation
        return next(mCHC.query(foreign_key[0], mCHC.uniq_id == foreign_key[1]))
    except StopIteration:
        return None


def get_producer_config(foreign_key: Tuple[str, str], compatible_calc: hazard_models.CompatibleHazardCalculation):
    mHCPC = hazard_models.HazardCurveProducerConfig
    try:
        return next(
            mHCPC.query(
                foreign_key[0],
                mHCPC.range_key == foreign_key[1],
                mHCPC.compatible_calc_fk == compatible_calc.foreign_key(),  # filter_condition
            )
        )
    except StopIteration:
        return None


def export_rlzs_rev4(
    extractor,
    compatible_calc: hazard_models.CompatibleHazardCalculation,
    producer_config: hazard_models.HazardCurveProducerConfig,
    hazard_calc_id: str,
    vs30: int,
    return_rlz=True,
) -> Union[List[hazard_models.HazardRealizationCurve], None]:

    # first check the FKs are OK
    compatible_calc = get_compatible_calc(compatible_calc.foreign_key())
    if compatible_calc is None:
        raise ValueError(f'compatible_calc: {compatible_calc.foreign_key()} was not found')

    if get_producer_config(producer_config.foreign_key(), compatible_calc) is None:
        raise ValueError(f'producer_config {producer_config} was not found')

    oq = json.loads(extractor.get('oqparam').json)
    sites = extractor.get('sitecol').to_dframe()
    rlzs = extractor.get('hcurves?kind=rlzs', asdict=True)

    rlz_keys = [k for k in rlzs.keys() if 'rlz-' in k]
    imtls = oq['hazard_imtls']  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}

    if not set(producer_config.imts).issuperset(set(imtls.keys())):
        log.error(f'imts do not align {imtls.keys()} <=> {producer_config.imts}')
        raise ValueError('bad IMT configuration')

    source_lt, gsim_lt, rlz_lt = parse_logic_tree_branches(extractor)

    # log.debug('rlz %s' % rlz_lt)
    # log.debug('src %s' % source_lt)
    # log.debug('gsim %s' % gsim_lt)

    # TODO : this assumes keys are in same order as rlzs
    rlz_branch_paths = rlz_lt['branch_path'].tolist()

    # assert 0

    def generate_models():
        for i_site in range(len(sites)):
            loc = normalise_site_code((sites.loc[i_site, 'lon'], sites.loc[i_site, 'lat']), True)
            # print(f'loc: {loc}')
            for i_rlz, bp in enumerate(rlz_branch_paths):

                source_branch, gmm_branch = bp.split('~')

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
                    if not imtls[imt] == producer_config.imt_levels:
                        log.error(
                            f'imt_levels not matched: {len(producer_config.imt_levels)}'
                            ' and values: {len(values)} do not align.'
                        )
                        raise ValueError('bad IMT levels configuration')

                    oq_realization = hazard_models.HazardRealizationCurve(
                        compatible_calc_fk=compatible_calc.foreign_key(),
                        producer_config_fk=producer_config.foreign_key(),
                        calculation_id=hazard_calc_id,
                        values=values,
                        imt=imt,
                        vs30=vs30,
                        source_branch=source_branch,
                        gmm_branch=gmm_branch,
                    )
                    # if oqmeta.model.vs30 == 0:
                    #    oq_realization.site_vs30 = sites.loc[i_site, 'vs30']
                    yield oq_realization.set_location(loc)

    # used for testing
    if return_rlz:
        return list(generate_models())

    save_parallel("", generate_models(), hazard_models.HazardRealizationCurve, NUM_BATCH_WORKERS, BATCH_SIZE)
    return None