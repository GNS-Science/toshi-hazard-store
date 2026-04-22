"""Helpers for reshaping flattened disaggregation arrays stored in parquet rows."""

from typing import Sequence, Union

import numpy as np
import numpy.typing as npt

# All recognised axis names and the order the schema stores their bin lists.
_KNOWN_AXES = ('trt', 'mag', 'dist', 'eps')


def reshape_disagg_values(
    disagg_values: Union[Sequence[float], npt.ArrayLike],
    disagg_axes: Sequence[str],
    trt: Union[Sequence, None] = None,
    mag: Union[Sequence, None] = None,
    dist: Union[Sequence, None] = None,
    eps: Union[Sequence, None] = None,
) -> npt.NDArray:
    """Reshape a flattened disaggregation row back into its N-dimensional grid.

    ``disagg_values`` was stored in C-order over the axes given by ``disagg_axes``
    (e.g. ``['trt', 'mag', 'dist', 'eps']``). This function recovers that shape
    from the bin-centre lists that are stored alongside each row, then calls
    ``numpy.reshape`` with the inferred shape.

    Args:
        disagg_values: the flat list or array from the ``disagg_values`` column.
        disagg_axes: ordered axis names from the ``disagg_axes`` column
            (e.g. ``['trt', 'mag', 'dist', 'eps']``). Every name must be one of
            ``'trt'``, ``'mag'``, ``'dist'``, ``'eps'``.
        trt: bin labels from the ``trt`` column (``None`` when axis absent).
        mag: bin centres from the ``mag`` column (``None`` when axis absent).
        dist: bin centres from the ``dist`` column (``None`` when axis absent).
        eps: bin centres from the ``eps`` column (``None`` when axis absent).

    Returns:
        A numpy array with shape ``(len(ax0_bins), len(ax1_bins), …)`` where axes
        follow the order in ``disagg_axes``.

    Raises:
        ValueError: if an axis name in ``disagg_axes`` is not recognised, or if its
            corresponding bin list is ``None``.
        ValueError: if the total element count does not match the product of the
            inferred axis sizes (i.e. ``disagg_values`` is inconsistent with the bins).
    """
    bins = {'trt': trt, 'mag': mag, 'dist': dist, 'eps': eps}

    unknown = [ax for ax in disagg_axes if ax not in _KNOWN_AXES]
    if unknown:
        raise ValueError(f"Unrecognised axis name(s): {unknown}. Expected one of {_KNOWN_AXES}.")

    shape = []
    for ax in disagg_axes:
        b = bins[ax]
        if b is None:
            raise ValueError(f"Axis '{ax}' is listed in disagg_axes but its bin list is None.")
        shape.append(len(b))

    return np.asarray(disagg_values).reshape(shape)
