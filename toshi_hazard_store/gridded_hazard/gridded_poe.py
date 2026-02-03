"""Calculate hazard at a given probability of exceedance level from a hazard curve."""

from typing import Iterable, List

import numpy as np

# HAZARD_CURVE_MAX_POE was `0.632` but location `-40.1~175.0` has non-monotonic issue in gridded_poe calculation at aggr=0.9 
HAZARD_CURVE_MAX_POE = 0.6318

def trim_poes(min_poe: float, max_poe: float, ground_accels: Iterable[float], annual_poes: Iterable[float]):
    """
    Returns a copy of annual_poes with values removed that are below min_poe or above max_poe.
    Returns a copy of ground_accels with elements removed at the same indexes that were removed from annual_poes.
    :param min_poe: the minimum poe
    :param max_poe: the maximum poe
    :param ground_accels: ground accels
    :param annual_poes: annual poes
    :return: a filter copy of ground_accels, and a filtered copy of annual_poes
    """
    acc_result = []
    poe_result = []
    for a, p in zip(ground_accels, annual_poes):
        if min_poe <= p <= max_poe:
            acc_result.append(a)
            poe_result.append(p)
    return acc_result, poe_result


def compute_hazard_at_poe(
    poe: float, ground_accels: List[float], annual_poes: List[float], investigation_time: int
) -> float:
    """Compute hazard at given poe using numpy.interpolate().

    see https://numpy.org/doc/stable/reference/generated/numpy.interp.html?highlight=interp
    """
    trimmed_ground_accels, trimmed_annual_poes = trim_poes(1e-10, HAZARD_CURVE_MAX_POE, ground_accels, annual_poes)
    return_period = -investigation_time / np.log(1 - poe)

    xp = np.flip(np.log(trimmed_annual_poes))  # type: ignore
    yp = np.flip(np.log(trimmed_ground_accels))  # type: ignore

    was_trimmed = len(trimmed_annual_poes) < len(annual_poes)
    if not np.all(np.diff(xp) >= 0):  # raise if x_accel_levels not increasing or at least not dropping,
        raise ValueError(
            f'Poe values not monotonic.\n xp: {xp}\n annual_poes: {annual_poes}\n'
            f'ground_accel: {ground_accels}\n Trimmed: {was_trimmed}'
        )

    return np.exp(np.interp(np.log(1 / return_period), xp, yp))  # type: ignore
