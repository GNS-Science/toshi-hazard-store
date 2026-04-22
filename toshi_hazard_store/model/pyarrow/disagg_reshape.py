"""Helpers for reshaping flattened disaggregation arrays stored in parquet rows."""

from typing import Union

import numpy as np
import numpy.typing as npt


def parse_disagg_bins(disagg_bins: Union[dict, list, tuple]) -> dict:
    """Cast stringified bin centres back to floats where possible, preserving axis order.

    Pairs with the extractor's stringification (bytes → decode, numeric → ``str()``):
    any bin list whose members all parse as ``float`` is returned as a list of floats;
    bin lists that don't (e.g. TRT labels like ``'Active Shallow Crust'``) are kept as
    strings. No axis-name special cases — the decision is driven purely by the value
    contents, so new axis types flow through without code changes.

    Args:
        disagg_bins: the ``disagg_bins`` column cell for one row. Accepts either a
            ``dict`` or an iterable of ``(key, value)`` pairs (what pyarrow's
            ``MapScalar.as_py()`` / ``MapArray.to_pylist()`` return). Key order
            defines axis order and is preserved in the returned dict.

    Returns:
        ``dict`` mapping axis name → list of bin centres. Numeric-only lists become
        ``list[float]``; mixed/string lists become ``list[str]``.
    """
    items = list(disagg_bins.items()) if hasattr(disagg_bins, 'items') else list(disagg_bins)
    result: dict = {}
    for k, v in items:
        try:
            result[k] = [float(x) for x in v]
        except (TypeError, ValueError):
            result[k] = list(v)
    return result


def reshape_disagg_values(
    disagg_values: npt.ArrayLike,
    disagg_bins: Union[dict, list, tuple],
) -> npt.NDArray:
    """Reshape a flattened disaggregation row back into its N-dimensional grid.

    ``disagg_values`` was stored in C-order over the axes defined by the key order
    of ``disagg_bins``. Axis order and bin sizes both come from the map: its keys
    give the axis order, ``len(bins[key])`` gives each dimension size.

    Args:
        disagg_values: flat sequence from the ``disagg_values`` column.
        disagg_bins: the ``disagg_bins`` column cell for this row. Accepts either a
            ``dict`` (e.g. constructed in Python) or an iterable of ``(key, value)``
            pairs (what pyarrow's ``MapScalar.as_py()`` / ``MapArray.to_pylist()``
            return). Key order defines axis order.

    Returns:
        N-dimensional numpy array whose axes follow ``disagg_bins`` key order.
    """
    items = list(disagg_bins.items()) if hasattr(disagg_bins, 'items') else list(disagg_bins)
    shape = tuple(len(v) for _, v in items)
    return np.asarray(disagg_values).reshape(shape)
