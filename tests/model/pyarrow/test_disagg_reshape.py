"""Tests for toshi_hazard_store.model.pyarrow.disagg_reshape."""

import numpy as np
import pytest

from toshi_hazard_store.model.pyarrow.disagg_reshape import reshape_disagg_values


def _make_flat(shape):
    """Return a sequential float array of the given shape, then flattened."""
    return np.arange(int(np.prod(shape)), dtype=np.float32).tolist()


class TestReshapeDisaggValues:
    def test_4d_round_trip(self):
        trt = ['Active', 'Subduction']
        mag = [5.5, 6.5, 7.5]
        dist = [10.0, 50.0, 100.0, 200.0]
        eps = [-1.0, 0.0, 1.0]
        shape = (len(trt), len(mag), len(dist), len(eps))
        flat = _make_flat(shape)

        result = reshape_disagg_values(flat, ['trt', 'mag', 'dist', 'eps'], trt=trt, mag=mag, dist=dist, eps=eps)

        assert result.shape == shape
        assert result[0, 0, 0, 0] == 0.0
        assert result[1, 2, 3, 2] == flat[-1]

    def test_2d_mag_dist_only(self):
        mag = [5.5, 6.5]
        dist = [10.0, 50.0, 100.0]
        flat = _make_flat((len(mag), len(dist)))

        result = reshape_disagg_values(flat, ['mag', 'dist'], mag=mag, dist=dist)

        assert result.shape == (2, 3)

    def test_axes_order_matters(self):
        trt = ['A', 'B', 'C']
        mag = [5.0, 6.0]
        flat = list(range(6))

        result_tm = reshape_disagg_values(flat, ['trt', 'mag'], trt=trt, mag=mag)
        result_mt = reshape_disagg_values(flat, ['mag', 'trt'], trt=trt, mag=mag)

        assert result_tm.shape == (3, 2)
        assert result_mt.shape == (2, 3)
        assert result_tm[1, 0] != result_mt[1, 0]

    def test_accepts_numpy_input(self):
        mag = [5.5, 6.5, 7.5]
        eps = [-1.0, 0.0, 1.0]
        flat = np.zeros(9, dtype=np.float64)

        result = reshape_disagg_values(flat, ['mag', 'eps'], mag=mag, eps=eps)

        assert result.shape == (3, 3)
        assert result.dtype == np.float64

    def test_accepts_pyarrow_list(self):
        import pyarrow as pa

        trt = ['A', 'B']
        mag = [5.5, 6.5, 7.5]
        flat = pa.array(list(range(6)), type=pa.float32())

        result = reshape_disagg_values(flat, ['trt', 'mag'], trt=trt, mag=mag)

        assert result.shape == (2, 3)

    def test_unknown_axis_raises(self):
        with pytest.raises(ValueError, match="Unrecognised axis name"):
            reshape_disagg_values([1.0], ['bad_axis'])

    def test_missing_bin_list_raises(self):
        with pytest.raises(ValueError, match="bin list is None"):
            reshape_disagg_values(list(range(6)), ['mag', 'dist'], mag=[5.5, 6.5, 7.5])

    def test_shape_mismatch_raises(self):
        mag = [5.5, 6.5]
        dist = [10.0, 50.0, 100.0]
        flat = list(range(10))  # 10 != 2*3

        with pytest.raises(Exception):
            reshape_disagg_values(flat, ['mag', 'dist'], mag=mag, dist=dist)
