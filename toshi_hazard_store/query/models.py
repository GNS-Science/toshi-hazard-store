"""Data models for hazard query operations."""

from dataclasses import dataclass
from typing import Union

# Constants
IMT_44_LVLS = [
    0.0001,
    0.0002,
    0.0004,
    0.0006,
    0.0008,
    0.001,
    0.002,
    0.004,
    0.006,
    0.008,
    0.01,
    0.02,
    0.04,
    0.06,
    0.08,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
    1.2,
    1.4,
    1.6,
    1.8,
    2.0,
    2.2,
    2.4,
    2.6,
    2.8,
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
    6.0,
    7.0,
    8.0,
    9.0,
    10.0,
]


@dataclass
class IMTValue:
    """Represents an intensity measure type (IMT) value.

    Attributes:
        lvl: The level of the IMT value.
        val: The value of the IMT at that level.
    """

    lvl: float  # noqa: F821
    val: float  # noqa: F821


@dataclass
class AggregatedHazard:
    """
    Represents an aggregated hazard dataset.

    Attributes:
        compatible_calc_id (str): the ID of a compatible calculation for PSHA engines interoperability.
        hazard_model_id (str): the model that these curves represent.
        nloc_001 (str): the location string to three places e.g. "-38.330~17.550".
        nloc_0 (str): the location string to zero places e.g.  "-38.0~17.0" (used for partitioning).
        imt (str): the intensity measure type label e.g. 'PGA', 'SA(5.0)'.
        vs30 (int): the VS30 integer.
        agg (str): the aggregation type.
        values (list[Union[float, IMTValue]]): a list of 44 IMTL values.

    Notes:
        This class is designed to match the table schema for aggregated hazard datasets.
    """

    compatable_calc_id: str
    hazard_model_id: str

    nloc_001: str
    nloc_0: str
    imt: str
    vs30: int
    agg: str
    values: list["IMTValue"]

    def to_imt_values(self):
        """
        Converts the IMTL values in this object's `values` attribute from a list of floats to a list of `IMTValue`
        objects.
        Returns:
            AggregatedHazard: this object itself.
        """
        new_values = zip(IMT_44_LVLS, self.values)
        self.values = [IMTValue(*x) for x in new_values]
        return self
