"""Tests for toshi_hazard_store.model.pyarrow.disagg_reshape."""

import numpy as np
import pytest

from toshi_hazard_store.model.pyarrow.disagg_reshape import parse_disagg_bins, reshape_disagg_values


def _make_flat(shape):
    """Return a 1D sequential float array with the number of elements euqal to the number of elements of a ndarray
    with the dimensions shape. This simulates a flattened disaggregation array."""
    return np.arange(int(np.prod(shape)), dtype=np.float32).tolist()


class TestReshapeDisaggValues:
    def test_4d_round_trip(self):
        bins = {
            'trt': ['Active', 'Subduction'],
            'mag': ['5.5', '6.5', '7.5'],
            'dist': ['10.0', '50.0', '100.0', '200.0'],
            'eps': ['-1.0', '0.0', '1.0'],
        }
        shape = tuple(len(v) for v in bins.values())
        flat = _make_flat(shape)

        result = reshape_disagg_values(flat, bins)

        assert result.shape == shape
        assert result[0, 0, 0, 0] == 0.0
        assert result[1, 2, 3, 2] == flat[-1]

    def test_2d_mag_dist_only(self):
        bins = {'mag': ['5.5', '6.5'], 'dist': ['10.0', '50.0', '100.0']}
        flat = _make_flat((2, 3))

        result = reshape_disagg_values(flat, bins)

        assert result.shape == (2, 3)

    def test_key_order_defines_axis_order(self):
        flat = list(range(6))

        r_tm = reshape_disagg_values(flat, {'trt': ['A', 'B', 'C'], 'mag': ['5.0', '6.0']})
        r_mt = reshape_disagg_values(flat, {'mag': ['5.0', '6.0'], 'trt': ['A', 'B', 'C']})

        assert r_tm.shape == (3, 2)
        assert r_mt.shape == (2, 3)
        assert r_tm[1, 0] != r_mt[1, 0]

    def test_accepts_list_of_tuples(self):
        """pyarrow MapScalar.as_py() returns list-of-tuples; reshape must accept that."""
        pairs = [('mag', ['5.5', '6.5']), ('dist', ['10.0', '50.0', '100.0'])]
        flat = list(range(6))

        result = reshape_disagg_values(flat, pairs)

        assert result.shape == (2, 3)

    def test_accepts_numpy_input(self):
        bins = {'mag': ['5.5', '6.5', '7.5'], 'eps': ['-1.0', '0.0', '1.0']}
        flat = np.zeros(9, dtype=np.float64)

        result = reshape_disagg_values(flat, bins)

        assert result.shape == (3, 3)
        assert result.dtype == np.float64

    def test_accepts_pyarrow_list(self):
        import pyarrow as pa

        bins = {'trt': ['A', 'B'], 'mag': ['5.5', '6.5', '7.5']}
        flat = pa.array(list(range(6)), type=pa.float32())

        result = reshape_disagg_values(flat, bins)

        assert result.shape == (2, 3)

    def test_shape_mismatch_raises(self):
        bins = {'mag': ['5.5', '6.5'], 'dist': ['10.0', '50.0', '100.0']}
        flat = list(range(10))  # 10 != 2*3

        with pytest.raises(Exception):
            reshape_disagg_values(flat, bins)


class TestParseDisaggBins:
    def test_numeric_axes_become_floats(self):
        bins = {'mag': ['5.5', '6.5', '7.5'], 'dist': ['10.0', '50.0', '100.0']}

        result = parse_disagg_bins(bins)

        assert result == {'mag': [5.5, 6.5, 7.5], 'dist': [10.0, 50.0, 100.0]}
        assert all(isinstance(x, float) for x in result['mag'])

    def test_trt_labels_stay_strings(self):
        bins = {'trt': ['Active Shallow Crust', 'Subduction Interface']}

        result = parse_disagg_bins(bins)

        assert result == {'trt': ['Active Shallow Crust', 'Subduction Interface']}
        assert all(isinstance(x, str) for x in result['trt'])

    def test_mixed_axes_each_cast_independently(self):
        bins = {
            'trt': ['Active', 'Subduction'],
            'mag': ['5.5', '6.5'],
            'dist': ['10.0', '50.0', '100.0'],
            'eps': ['-2.0', '-1.0', '0.0', '1.0', '2.0'],
        }

        result = parse_disagg_bins(bins)

        assert result['trt'] == ['Active', 'Subduction']
        assert result['mag'] == [5.5, 6.5]
        assert result['eps'] == [-2.0, -1.0, 0.0, 1.0, 2.0]
        assert all(isinstance(x, str) for x in result['trt'])
        assert all(isinstance(x, float) for x in result['eps'])

    def test_key_order_preserved(self):
        bins = {'eps': ['0.0'], 'trt': ['A'], 'mag': ['5.5'], 'dist': ['10.0']}

        result = parse_disagg_bins(bins)

        assert list(result.keys()) == ['eps', 'trt', 'mag', 'dist']

    def test_accepts_list_of_tuples(self):
        """pyarrow MapScalar.as_py() returns list-of-tuples; parse must accept it."""
        pairs = [('mag', ['5.5', '6.5']), ('trt', ['Active'])]

        result = parse_disagg_bins(pairs)

        assert result == {'mag': [5.5, 6.5], 'trt': ['Active']}
        assert list(result.keys()) == ['mag', 'trt']

    def test_scientific_notation_parses(self):
        bins = {'mag': ['1e-3', '1.5e2', '2.5E+1']}

        result = parse_disagg_bins(bins)

        assert result['mag'] == [0.001, 150.0, 25.0]

    def test_composes_with_reshape(self):
        """Parsed bins can be passed straight to reshape_disagg_values."""
        bins = {'mag': ['5.5', '6.5'], 'dist': ['10.0', '50.0', '100.0']}
        flat = list(range(6))

        parsed = parse_disagg_bins(bins)
        result = reshape_disagg_values(flat, parsed)

        assert result.shape == (2, 3)
        assert parsed['mag'] == [5.5, 6.5]
