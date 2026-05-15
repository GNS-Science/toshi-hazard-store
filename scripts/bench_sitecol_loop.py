"""Bench the sitecol → CodedLocation loop in extract_classical_hdf5.

Times the per-row pandas access pattern in isolation.

Usage:
    uv run python scripts/bench_sitecol_loop.py [hdf5_path]
"""

import sys
import timeit
from pathlib import Path

from nzshm_common.location import coded_location

from toshi_hazard_store.oq_import.h5py_reader import OqHdf5Reader

# DEFAULT_HDF5 = (
#     Path(__file__).parent.parent
#     / 'tests/fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
# )
DEFAULT_HDF5 = Path("/home/chrisdc/tmp/calc_1.hdf5")


def under_test(df0):
    """Mirrors extract_classical_hdf5.generate_rlz_record_batches site-indexing block."""
    lats = df0['lat'].tolist()
    lons = df0['lon'].tolist()
    site_vs30s = df0['vs30'].tolist()
    nloc_001_locations = [
        coded_location.CodedLocation(lat=lat, lon=lon, resolution=0.001) for lat, lon in zip(lats, lons)
    ]
    return nloc_001_locations, site_vs30s


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_HDF5
    df0 = OqHdf5Reader(str(path)).sitecol()
    n_sites = df0.shape[0]

    timer = timeit.Timer('under_test(df0)', globals={'under_test': under_test, 'df0': df0})
    n_loops, _ = timer.autorange()  # picks n_loops so each repeat takes ≥ 0.2s
    samples = timer.repeat(repeat=5, number=n_loops)
    best = min(samples) / n_loops  # min is the timeit convention — least scheduler noise

    print(f'fixture: {path}')
    print(f'n_sites={n_sites}  n_loops={n_loops}  repeats=5')
    print(f'best: {best * 1000:.3f} ms/call   per-row: {best / n_sites * 1e6:.2f} µs')
    print(f'all repeats (ms/call): {[round(s / n_loops * 1000, 3) for s in samples]}')


if __name__ == '__main__':
    main()

# Old implimentation
# fixture: /home/chrisdc/tmp/calc_1.hdf5
# n_sites=3991  n_loops=1  repeats=5
# best: 528.994 ms/call   per-row: 132.55 µs
# all repeats (ms/call): [530.03, 528.994, 531.495, 529.58, 532.193]
