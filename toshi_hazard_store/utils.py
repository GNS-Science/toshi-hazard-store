"""Common utilities."""

import decimal
from collections import namedtuple

CustomLocation = namedtuple("CustomLocation", "site_code lon lat")
CustomHazardCurve = namedtuple("CustomHazardCurve", "loc poes")


def normalise_site_code(oq_site_object: tuple, force_normalized: bool = False):
    """Return a valid code for storage."""
    # print(oq_site_object)

    def stringify(lat, lon):
        return f'[{round(lat, 3):.3f}~{round(lon, 3):.3f}]'

    force_normalized = force_normalized if len(oq_site_object) == 3 else True
    if len(oq_site_object) not in [2, 3]:
        raise ValueError(f"Unknown site object {oq_site_object}")

    if len(oq_site_object) == 3:
        _, lon, lat = oq_site_object
    elif len(oq_site_object) == 2:
        lon, lat = oq_site_object
    else:
        raise ValueError(f"Unknown site object {oq_site_object}")

    if force_normalized:
        return CustomLocation(stringify(lat, lon), lon=lon, lat=lat)
    else:
        return CustomLocation(oq_site_object[0].decode(), lon=lon, lat=lat)


def downsample_loc(location: CustomLocation, grid_degrees: float = 0.5):
    '''For spreading partition keys (experimental).'''

    grid_res = decimal.Decimal(str(grid_degrees).rstrip("0"))
    places = abs(decimal.Decimal(grid_res).as_tuple().exponent)

    display_places = max(abs(grid_res.as_tuple().exponent), 1)
    div_res = 1 / float(grid_res)
    places = abs(decimal.Decimal(div_res).as_tuple().exponent)

    # print(f'grid_res {grid_res} => div_res {div_res} places {places}') #  round_res {round_res}

    d_lon = round(location.lon * div_res, places) / div_res
    d_lat = round(location.lat * div_res, places) / div_res

    return CustomLocation(site_code=f'{d_lat:.{display_places}f}~{d_lon:.{display_places}f}', lat=d_lat, lon=d_lon)
