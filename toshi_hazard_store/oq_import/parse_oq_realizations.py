"""
Convert openquake realisations using nzshm_model.branch_registry

NB maybe this belongs in the nzshm_model.psha_adapter.openquake package ??
"""

import collections
import logging
from typing import TYPE_CHECKING, Any, Dict

from nzshm_model import branch_registry
from nzshm_model.psha_adapter.openquake import gmcm_branch_from_element_text

from .transform import parse_logic_tree_branches

if TYPE_CHECKING:
    from openquake.calculators.extract import Extractor

log = logging.getLogger(__name__)

registry = branch_registry.Registry()

RealizationRecord = collections.namedtuple('RealizationRecord', 'idx, path, sources, gmms')


def build_rlz_mapper(extractor: 'Extractor') -> Dict[int, RealizationRecord]:
    """
    Builds a realization mapper from an extractor.

    Args:
        extractor (Extractor): An OpenQuake Extractor object.

    Returns:
        Dict[int, RealizationRecord]: A dictionary of realization records.
    """
    return get_rlz_mapper(*parse_logic_tree_branches(extractor))


def get_rlz_mapper(
    source_branches: dict[str, str], gsim_branches: dict[str, str], realizations: list[dict[str, Any]]
) -> Dict[int, RealizationRecord]:
    gmm_map = build_rlz_gmm_map(gsim_branches)
    source_map = build_rlz_source_map(source_branches)
    rlz_map = build_rlz_map(realizations, source_map, gmm_map)
    return rlz_map


# NOTE: this function can mostly stay the same, I think. It simply maps the gsim path (e.g. `gA1`) to an "identity" that we can use
# input could be a dict?
def build_rlz_gmm_map(gsim_branches: dict[str, str]) -> Dict[str, branch_registry.BranchRegistryEntry]:
    rlz_gmm_map = {}
    for gsim_id, gsim in gsim_branches.items():
        log.debug(f"build_rlz_gmm_map(gsim_lt): {gsim_id} {gsim}")
        branch = gmcm_branch_from_element_text(gsim)
        entry = registry.gmm_registry.get_by_identity(branch.registry_identity)
        rlz_gmm_map[gsim_id] = entry
    return rlz_gmm_map


# NOTE: input could be a dict?
# builds a dict of branch path (e.g. 'AA') to a BranchRegistryEntry. Need the branch string to look up the entry
def build_rlz_source_map(source_branches: dict[str, str]) -> Dict[str, branch_registry.BranchRegistryEntry]:
    rlz_source_map = dict()
    for source_str in source_branches.values():
        log.debug(f"build_rlz_source_map(source_lt): {source_str}")

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

        rlz_source_map[source_str] = entry
    return rlz_source_map


def build_rlz_map(
    realizations: list[dict[str, Any]],
    source_map: dict[str, branch_registry.BranchRegistryEntry],
    gmm_map: dict[str, branch_registry.BranchRegistryEntry],
) -> dict[int, RealizationRecord]:
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
    # TODO: these realizations only handle one source and one gmm branch. We may want to handle at least multiple
    # gmm branches (e.g. sources with multiple TRTs). We may also want to hanlde multiple source branches, such
    # as when we use a logic tree with an actual branching structure (e.g. extended model)
    rlz_map = dict()
    for rlz in realizations:
        idx = rlz['ordinal']
        path = '_'
        sources = source_map[rlz['source_path'][0]]
        gmms = gmm_map[rlz['gsim_path'][0]]
        rlz_map[idx] = RealizationRecord(idx=idx, path=path, sources=sources, gmms=gmms)
    return rlz_map
