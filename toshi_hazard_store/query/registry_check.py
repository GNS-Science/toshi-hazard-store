"""Utility for checking branch digests against the nzshm_model branch registry."""

import warnings
from typing import Literal


def check_registry_status(
    digests: set[str],
    registry_type: Literal["source", "gmm"] = "source",
) -> set[str]:
    """Return the subset of digests not found in the branch registry.

    Issues a UserWarning if any unregistered digests are found. Callers can
    control behaviour via warnings.filterwarnings() — e.g. to escalate to an
    error, silence, or show the warning only once.

    Args:
        digests: set of hash_digest strings to check.
        registry_type: "source" to check the source registry, "gmm" for the GMM registry.

    Returns:
        Set of digest strings not found in the registry.
    """
    from nzshm_model.branch_registry import Registry

    registry = Registry()
    branch_registry = registry.source_registry if registry_type == "source" else registry.gmm_registry
    unregistered = set()
    for digest in digests:
        try:
            branch_registry.get_by_hash(digest)
        except KeyError:
            unregistered.add(digest)
    if unregistered:
        warnings.warn(
            f"Found {len(unregistered)} unregistered {registry_type} branch(es): {unregistered}",
            UserWarning,
            stacklevel=2,
        )
    return unregistered
