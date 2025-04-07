"""
Convert openquake realisations using nzshm_model.branch_registry

NB maybe this belongs in the nzshm_model.psha_adapter.openquake package ??
"""

import collections
import logging
from typing import TYPE_CHECKING, Dict

from nzshm_model import branch_registry
from nzshm_model.psha_adapter.openquake import gmcm_branch_from_element_text

from .transform import parse_logic_tree_branches

if TYPE_CHECKING:
    import pandas
    from openquake.calculators.extract import Extractor

log = logging.getLogger(__name__)

registry = branch_registry.Registry()

RealizationRecord = collections.namedtuple('RealizationRecord', 'idx, path, sources, gmms')


def rlz_mapper_from_dataframes(
    source_lt: 'pandas.DataFrame', gsim_lt: 'pandas.DataFrame', rlz_lt: 'pandas.DataFrame'
) -> Dict[int, RealizationRecord]:
    """
    Maps realizations from dataframes.

    Args:
        source_lt (pandas.DataFrame): Source logic tree dataframe.
        gsim_lt (pandas.DataFrame): GSIM logic tree dataframe.
        rlz_lt (pandas.DataFrame): Realization logic tree dataframe.

    Returns:
        Dict[int, RealizationRecord]: A dictionary of realization records.
    """
    gmm_map = build_rlz_gmm_map(gsim_lt)
    source_map = build_rlz_source_map(source_lt)
    rlz_map = build_rlz_map(rlz_lt, source_map, gmm_map)
    return rlz_map


def build_rlz_mapper(extractor: 'Extractor') -> Dict[int, RealizationRecord]:
    """
    Builds a realization mapper from an extractor.

    Args:
        extractor (Extractor): An OpenQuake Extractor object.

    Returns:
        Dict[int, RealizationRecord]: A dictionary of realization records.
    """
    return rlz_mapper_from_dataframes(*parse_logic_tree_branches(extractor))


def build_rlz_gmm_map(gsim_lt: 'pandas.DataFrame') -> Dict[str, branch_registry.BranchRegistryEntry]:
    """
    Builds a map of realizations to GMMs.

    Args:
        gsim_lt (pandas.DataFrame): GSIM logic tree dataframe.

    Returns:
        Dict[str, BranchRegistryEntry]: A dictionary mapping realization IDs to branch registry entries.
    """
    branch_ids = gsim_lt.branch.tolist()
    rlz_gmm_map = dict()
    for idx, uncertainty in enumerate(gsim_lt.uncertainty.tolist()):
        log.debug(f"build_rlz_gmm_map(gsim_lt): {idx} {uncertainty}")
        branch = gmcm_branch_from_element_text(uncertainty)
        entry = registry.gmm_registry.get_by_identity(branch.registry_identity)
        rlz_gmm_map[branch_ids[idx][1:-1]] = entry
    return rlz_gmm_map


def build_rlz_source_map(source_lt: 'pandas.DataFrame') -> Dict[str, branch_registry.BranchRegistryEntry]:
    """
    Build a map of realizations to source registry entries.

    Args:
        source_lt (pandas.DataFrame): DataFrame containing the source logic tree branches.

    Returns:
        Dict[str, branch_registry.BranchRegistryEntry]: A dictionary mapping realization IDs to
            their corresponding source registry entries.
    """
    branch_ids = source_lt.index.tolist()
    rlz_source_map = dict()
    for idx, source_str in enumerate(source_lt.branch.tolist()):
        log.debug(f"build_rlz_source_map(source_lt): {idx} {source_str}")

        # handle special case found in
        # INFO:scripts.ths_r4_migrate:task: T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NTA0 hash: bdc5476361cd
        # gt: R2VuZXJhbFRhc2s6MTMyODQxNA==  hazard_id: T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU2MA==
        if source_str[0] == '|':
            source_str = source_str[1:]

        # handle special case where tag was stored in calc instead of toshi_ids
        # e.g. T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz
        if source_str[0] == '[' and source_str[-1] == ']':
            entry = registry.source_registry.get_by_extra(source_str)
        else:
            sources = "|".join(sorted(source_str.split('|')))
            entry = registry.source_registry.get_by_identity(sources)

        rlz_source_map[branch_ids[idx]] = entry
    return rlz_source_map


def build_rlz_map(rlz_lt: 'pandas.DataFrame', source_map: Dict, gmm_map: Dict) -> Dict[int, RealizationRecord]:
    """
    Builds a dictionary mapping realization indices to their corresponding
    RealizationRecord objects.

    Args:
        rlz_lt (pandas.DataFrame): The dataframe containing the logic tree branches.
        source_map (Dict): A map of source identifiers to BranchRegistryEntry objects.
        gmm_map (Dict): A map of GMM identifiers to BranchRegistryEntry objects.

    Returns:
        Dict[int, RealizationRecord]: A dictionary mapping realization indices
            to their corresponding RealizationRecord objects.
    """
    paths = rlz_lt.branch_path.tolist()
    rlz_map = dict()
    for idx, path in enumerate(paths):
        src_key, gmm_key = path.split('~')
        rlz_map[idx] = RealizationRecord(idx=idx, path=path, sources=source_map[src_key], gmms=gmm_map[gmm_key])
    return rlz_map
