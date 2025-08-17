"""
Convert openquake realisations using nzshm_model.branch_registry

NB maybe this belongs in the nzshm_model.psha_adapter.openquake package ??
"""

import collections
import logging
from typing import TYPE_CHECKING

from nzshm_model import branch_registry
from nzshm_model.psha_adapter.openquake import gmcm_branch_from_element_text

from .transform import Realization, parse_logic_tree_branches

if TYPE_CHECKING:
    from openquake.calculators.extract import Extractor


log = logging.getLogger(__name__)

registry = branch_registry.Registry()

RealizationRecord = collections.namedtuple('RealizationRecord', 'idx, path, sources, gmms')


def build_rlz_mapper(extractor: 'Extractor') -> dict[int, RealizationRecord]:
    """Builds a realization mapper from an extractor.

    Args:
        extractor (Extractor): An OpenQuake Extractor object.

    Returns:
        dict[int, RealizationRecord]: A dictionary of realization records.
    """
    source_branches, gsim_branches, realizations = parse_logic_tree_branches(extractor)
    gmm_map = build_rlz_gmm_map(gsim_branches)
    source_map = build_rlz_source_map(source_branches)
    rlz_map = build_rlz_map(realizations, source_map, gmm_map)
    return rlz_map


def build_rlz_gmm_map(gsim_branches: dict[str, str]) -> dict[str, branch_registry.BranchRegistryEntry]:
    """Build a map of realizations to GMMs.

    Args:
        gsim_branches: the ground motion branch dict keyed by branch id and valued by branch name.

    Returns:
        A dictionary mapping realization IDs to branch registry entries.
    """
    rlz_gmm_map = {}
    for gsim_id, gsim in gsim_branches.items():
        log.debug(f"build_rlz_gmm_map(gsim_lt): {gsim_id} {gsim}")
        branch = gmcm_branch_from_element_text(gsim)
        entry = registry.gmm_registry.get_by_identity(branch.registry_identity)
        rlz_gmm_map[gsim_id] = entry
    return rlz_gmm_map


def build_rlz_source_map(source_branches: dict[str, str]) -> dict[str, branch_registry.BranchRegistryEntry]:
    """Build a map of realizations to sources.

    Args:
        source_branches: the source branch dict keyed by branch id and valued by branch name.

    Returns:
        A dictionary mapping realization IDs to branch registry entries.
    """
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
    realizations: list[Realization],
    source_map: dict[str, branch_registry.BranchRegistryEntry],
    gmm_map: dict[str, branch_registry.BranchRegistryEntry],
) -> dict[int, RealizationRecord]:
    """Builds a dictionary mapping realization indices to their corresponding RealizationRecord objects.

    Args:
        rlz_lt (pandas.DataFrame): The dataframe containing the logic tree branches.
        source_map (dict): A map of source identifiers to BranchRegistryEntry objects.
        gmm_map (dict): A map of GMM identifiers to BranchRegistryEntry objects.

    Returns:
        A dictionary mapping realization indices to their corresponding RealizationRecord objects.
    """
    # TODO: these realizations only handle one source and one gmm branch. We may want to handle at least multiple
    # gmm branches (e.g. sources with multiple TRTs). We may also want to hanlde multiple source branches, such
    # as when we use a logic tree with an actual branching structure (e.g. extended model)
    rlz_map = dict()
    for rlz in realizations:
        idx = rlz.ordinal

        # this nolonger mirrors the OpenQuake path (e.g. 'AA~A') becasue we are using the full source name
        # and the full gsim id.
        path = '~'.join((rlz.source_path[0], rlz.gsim_path[0]))
        sources = source_map[rlz.source_path[0]]
        gmms = gmm_map[rlz.gsim_path[0]]
        rlz_map[idx] = RealizationRecord(idx=idx, path=path, sources=sources, gmms=gmms)
    return rlz_map
