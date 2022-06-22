"""Common utilities."""

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


def downsample_loc(location: CustomLocation):
    '''For spreading partition keys (experimental).'''
    d_lon = round(location.lon * 2, 0) / 2
    d_lat = round(location.lat * 2, 0) / 2
    return f'{d_lat:.1f}~{d_lon:.1f}'
