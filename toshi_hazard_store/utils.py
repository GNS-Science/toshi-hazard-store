"""Common utilities."""

import decimal
from dataclasses import dataclass


@dataclass
class CodedLocation:

    lat: float
    lon: float
    code: str = ""

    # def set_code(self, code):
    #     self.code = code

    def downsample(self, resolution: float) -> 'CodedLocation':
        """Downsamples to the nearest point on a grid with given resolution (degrees).

        # ref https://stackoverflow.com/a/28750072 for  the techniques used here to calculate decimal places.
        """
        assert 0 < resolution < 180
        grid_res = decimal.Decimal(str(resolution).rstrip("0"))
        display_places = max(abs(grid_res.as_tuple().exponent), 1)

        div_res = 1 / float(grid_res)
        places = abs(decimal.Decimal(div_res).as_tuple().exponent)

        # print(f'grid_res {grid_res} => div_res {div_res} places {places}') #  round_res {round_res}

        d_lon = round(self.lon * div_res, places) / div_res
        d_lat = round(self.lat * div_res, places) / div_res

        return CodedLocation(code=f'{d_lat:.{display_places}f}~{d_lon:.{display_places}f}', lat=d_lat, lon=d_lon)


def normalise_site_code(oq_site_object: tuple, force_normalized: bool = False) -> CodedLocation:
    """Return a valid code for storage."""

    if len(oq_site_object) not in [2, 3]:
        raise ValueError(f"Unknown site object {oq_site_object}")

    force_normalized = force_normalized if len(oq_site_object) == 3 else True

    if len(oq_site_object) == 3:
        _, lon, lat = oq_site_object
    elif len(oq_site_object) == 2:
        lon, lat = oq_site_object

    rounded = CodedLocation(lon=lon, lat=lat).downsample(0.001)

    if not force_normalized:
        rounded.code = oq_site_object[0].decode()  # restore the original location code
    return rounded
