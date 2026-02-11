"""pydantic modles helpers for analysis of gridded datasets"""

# import json
# import logging
from typing import Optional, Union

import numpy as np
from nzshm_common.location import get_locations
from pydantic import BaseModel

# from pydantic_core import from_json


class GridIdentity(BaseModel):
    region_grid_id: str
    hazard_model_id: str
    agg: str
    imt: str
    vs30: int
    poe: float

    def to_idx(self):
        return f"{self.region_grid_id}:{self.hazard_model_id}:{self.agg}:{self.imt}:{self.vs30}:{self.poe}"

    @staticmethod
    def from_idx(idx_str: str):
        idx_vals = idx_str.split(':')
        return GridIdentity(
            region_grid_id=idx_vals[0],
            hazard_model_id=idx_vals[1],
            agg=idx_vals[2],
            imt=idx_vals[3],
            vs30=int(idx_vals[4]),
            poe=float(idx_vals[5]),
        )


class GridDiff(BaseModel):
    grid_id: GridIdentity
    l_values: np.ndarray
    r_values: np.ndarray
    model_config = dict(arbitrary_types_allowed=True)

    # def numeric_difference(self, rtol: float, atol: float) -> Optional[np.ndarray]:
    #     # A. Difference detection (numeric)
    #     # NB we're using masked_invalid() to mask any NaN values from the diff calcs
    #     _ma, _mb = ma.masked_invalid(self.l_values), ma.masked_invalid(self.r_values)
    #     result = np.isclose(_ma, _mb, rtol=rtol, atol=atol)
    #     if not result.all():
    #         # return the full array including nans
    #         return self.l_values - self.r_values
    #     return None

    def isclose(self, rtol: float, atol: float):
        return np.isclose(self.l_values, self.r_values, atol=atol, rtol=rtol)


class LocationDiff(BaseModel):
    l_value: Union['float', None]
    r_value: Union['float', None]


class LocationMap(BaseModel):
    location_code: str
    map: dict[str, LocationDiff]
    max_error: float = 0.0
    grids_in_error: int = 0

    def append_location_diff(self, location_diff: LocationDiff, grid_diff: GridDiff):
        self.map[grid_diff.grid_id.to_idx()] = location_diff
        self.grids_in_error += 1
        self.max_error = max(self.max_error, float(location_diff.l_value or 0) - float(location_diff.r_value or 0))


class GridDiffDiagnostic(BaseModel):
    """Capture information about grid differences from two grid record sources."""

    atol: float
    rtol: float
    region_grid_id: str
    r_source: str = ""
    l_source: str = ""
    location_map: dict[str, LocationMap]
    checked_grid_entries: int = 0
    failed_grid_entries: int = 0

    @property
    def location_codes(self):
        return [loc.code for loc in get_locations(locations=[self.region_grid_id])]

    def update_location_map(self, location: str, location_diff: LocationDiff, grid_diff: GridDiff):
        map_entry = self.location_map.get(location)
        if not map_entry:
            map_entry = LocationMap(location_code=location, map={})
            self.location_map[location] = map_entry
        map_entry.append_location_diff(location_diff, grid_diff)

    def check_diff(self, diff: GridDiff) -> Optional[str]:
        self.checked_grid_entries += 1
        # numeric_diff = diff.numeric_difference(rtol=self.rtol, atol=self.atol)
        # if numeric_diff is not None:
        errors = np.where(diff.isclose(rtol=self.rtol, atol=self.atol) == False)[0].tolist()  # noqa: E712
        if len(errors):
            self.failed_grid_entries += 1
            # print(errors)
            for idx in errors:
                location = self.location_codes[idx]
                location_diff = LocationDiff(l_value=diff.l_values.tolist()[idx], r_value=diff.r_values.tolist()[idx])
                self.update_location_map(location, location_diff, diff)

            return f'DIFF :: {diff.grid_id} :: {len(errors)}'
        return None
