import pytest

from toshi_hazard_store.utils import CustomLocation, downsample_loc


@pytest.mark.parametrize(
    "lat,lon,expected",
    [
        (-45.27, 171.1, '-45.5~171.0'),
        (-45.23, 171.1, '-45.0~171.0'),
        (-45.27, 171.4, '-45.5~171.5'),
        (-45.27, 171.8, '-45.5~172.0'),
    ],
)
def test_downsample(lat, lon, expected):
    # lat, lon  = -45.27, 171.1
    s = CustomLocation('ABC', lat=lat, lon=lon)
    assert downsample_loc(s) == expected
