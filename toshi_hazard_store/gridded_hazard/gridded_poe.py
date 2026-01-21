"""Calculate hazard at a given probability of exceedance level from a hazard curve."""

# import json
# from itertools import product
from typing import Iterable  # Any, Iterator, List, Tuple

import numpy as np

# import pandas as pd


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
    poe: float, ground_accels: Iterable[float], annual_poes: Iterable[float], investigation_time: int
) -> float:
    """Compute hazard at given poe using numpy.interpolate().

    see https://numpy.org/doc/stable/reference/generated/numpy.interp.html?highlight=interp
    """
    ground_accels, annual_poes = trim_poes(1e-10, 0.632, ground_accels, annual_poes)
    return_period = -investigation_time / np.log(1 - poe)

    xp = np.flip(np.log(annual_poes))  # type: ignore
    yp = np.flip(np.log(ground_accels))  # type: ignore

    if not np.all(np.diff(xp) >= 0):  # raise is x_accel_levels not increasing or at least not dropping,
        raise ValueError('Poe values not monotonous.')

    return np.exp(np.interp(np.log(1 / return_period), xp, yp))  # type: ignore
