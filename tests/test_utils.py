import pytest

from toshi_hazard_store.utils import CustomLocation, downsample_loc


@pytest.mark.parametrize(
    "lat,lon,expected",
    [
        (-45.27, 171.1, '-45.5~171.0'),
        (-45.23, 171.1, '-45.0~171.0'),
        (-45.27, 171.4, '-45.5~171.5'),
        (-45.27, 171.8, '-45.5~172.0'),
        (-41.3, 174.78, '-41.5~175.0'),  # WLG
    ],
)
def test_downsample_default_oh_point_five(lat, lon, expected):
    # lat, lon  = -45.27, 171.1
    print(f"lat {lat} lon {lon} -> {expected}")
    s = CustomLocation('ABC', lat=lat, lon=lon)
    assert downsample_loc(s).site_code == expected


@pytest.mark.parametrize(
    "lat,lon,expected",
    [
        (-45.27, 171.1, '-45.0~171.0'),
        (-45.23, 171.1, '-45.0~171.0'),
        (-45.77, 171.4, '-46.0~171.0'),
        (-45.27, 171.8, '-45.0~172.0'),
        (-41.3, 174.78, '-41.0~175.0'),  # WLG
    ],
)
def test_downsample_one_point_oh(lat, lon, expected):
    s = CustomLocation('ABC', lat=lat, lon=lon)
    assert downsample_loc(s, grid_degrees=1.0).site_code == expected


@pytest.mark.parametrize(
    "lat,lon,expected",
    [
        (-45.27, 171.1, '-45.3~171.1'),
        (-45.239, 171.13, '-45.2~171.1'),
        (-45.27, 171.4, '-45.3~171.4'),
        (-45.27, 171.8, '-45.3~171.8'),
        (-41.333, 174.78, '-41.3~174.8'),  # WLG
    ],
)
def test_downsample_oh_point_one(lat, lon, expected):
    # lat, lon  = -45.27, 171.1
    s = CustomLocation('ABC', lat=lat, lon=lon)
    assert downsample_loc(s, grid_degrees=0.1).site_code == expected


@pytest.mark.parametrize(
    "lat,lon,expected",
    [
        (-45.27, 171.111, '-45.25~171.10'),
        (-45.239, 171.73, '-45.25~171.75'),
        (45.126, 171.4, '45.15~171.40'),
        (-45.27, 171.03, '-45.25~171.05'),
        (-41.333, 174.78, '-41.35~174.80'),  # WLG
    ],
)
def test_downsample_oh_point_oh_five(lat, lon, expected):
    # lat, lon  = -45.27, 171.1
    s = CustomLocation('ABC', lat=lat, lon=lon)
    assert downsample_loc(s, grid_degrees=0.05).site_code == expected
