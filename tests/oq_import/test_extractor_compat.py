"""Compatibility tests: OqHdf5Reader vs openquake.calculators.extract.Extractor.

These tests run both implementations against the same committed HDF5 fixtures and
assert that every field the h5py reader produces matches the OpenQuake Extractor's
reference output — both structurally and numerically.

Requires the ``oq-compat`` dependency group (openquake-engine==3.25.1):

    uv run tox -e oq-compat
    # or:
    uv sync --group oq-compat
    uv run pytest tests/oq_import/test_extractor_compat.py -v

Normal ``uv run pytest`` skips all tests here gracefully.
"""

import json
from pathlib import Path

import numpy as np
import pytest

try:
    import openquake  # noqa
    from openquake.calculators.extract import Extractor

    HAVE_OQ = True
except ImportError:
    HAVE_OQ = False

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.revision_4 import extract_disagg_hdf5
from toshi_hazard_store.oq_import.h5py_reader import OqHdf5Reader

_CLASSICAL_HDF5 = (
    Path(__file__).parent.parent
    / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
)
_DISAGG_HDF5 = (
    Path(__file__).parent.parent
    / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTI4NDUy/calc_1.hdf5'
)

pytestmark = pytest.mark.skipif(
    not HAVE_OQ,
    reason='openquake-engine not installed — run: uv run tox -e oq-compat',
)


# ── Shared fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope='module')
def classical_pair():
    """(OqHdf5Reader, Extractor) for the classical fixture."""
    return OqHdf5Reader(str(_CLASSICAL_HDF5)), Extractor(str(_CLASSICAL_HDF5))


@pytest.fixture(scope='module')
def disagg_pair():
    """(OqHdf5Reader, Extractor, kind, imt) for the disagg fixture."""
    reader = OqHdf5Reader(str(_DISAGG_HDF5))
    extractor = Extractor(str(_DISAGG_HDF5))
    oqp = reader.oqparam()
    kinds = oqp.get('disagg_outputs', [])
    kind = next((k for k in kinds if 'Mag' in k and 'Dist' in k), kinds[0])
    imt = next(iter(oqp['iml_disagg']))
    return reader, extractor, kind, imt


# ── oqparam ───────────────────────────────────────────────────────────────────


def test_oqparam_identical_classical(classical_pair):
    """oqparam dict from h5py reader equals OQ Extractor output exactly."""
    reader, extractor = classical_pair
    h5_oqp = reader.oqparam()
    oq_oqp = json.loads(extractor.get('oqparam').json)
    assert h5_oqp == oq_oqp


def test_oqparam_identical_disagg(disagg_pair):
    reader, extractor, kind, imt = disagg_pair
    h5_oqp = reader.oqparam()
    oq_oqp = json.loads(extractor.get('oqparam').json)
    assert h5_oqp == oq_oqp


# ── sitecol ───────────────────────────────────────────────────────────────────


def test_sitecol_classical(classical_pair):
    """sitecol lat/lon/vs30 identical to OQ Extractor."""
    reader, extractor = classical_pair
    h5_df = reader.sitecol()
    oq_df = extractor.get('sitecol').to_dframe()
    assert np.allclose(h5_df['lat'].values, oq_df['lat'].values)
    assert np.allclose(h5_df['lon'].values, oq_df['lon'].values)
    assert np.allclose(h5_df['vs30'].values, oq_df['vs30'].values)


def test_sitecol_disagg(disagg_pair):
    reader, extractor, kind, imt = disagg_pair
    h5_df = reader.sitecol()
    oq_df = extractor.get('sitecol').to_dframe()
    assert np.allclose(h5_df['lat'].values, oq_df['lat'].values)
    assert np.allclose(h5_df['lon'].values, oq_df['lon'].values)
    assert np.allclose(h5_df['vs30'].values, oq_df['vs30'].values)


# ── hcurves_rlzs ─────────────────────────────────────────────────────────────


def test_hcurves_rlzs_numerical_equality(classical_pair):
    """Per-rlz hazard curves match OQ Extractor for every rlz and every site."""
    reader, extractor = classical_pair
    h5_rlzs = reader.hcurves_rlzs()
    oq_rlzs = extractor.get('hcurves?kind=rlzs', asdict=True)
    oq_keys = [k for k in oq_rlzs if 'rlz-' in k]
    assert set(h5_rlzs.keys()) == set(oq_keys), 'rlz key sets differ'
    for key in oq_keys:
        assert np.allclose(h5_rlzs[key], oq_rlzs[key], rtol=1e-5), f'hcurves_rlzs mismatch for {key}'


# ── realizations ──────────────────────────────────────────────────────────────


def test_realizations_ordinals_and_paths(classical_pair):
    """Realization ordinals, source paths and GSIM paths identical to OQ Extractor."""
    reader, extractor = classical_pair
    h5_rlzs = reader.realizations()
    oq_rlzs = list(extractor.get('full_lt').get_realizations())
    assert len(h5_rlzs) == len(oq_rlzs)
    for h5_r, oq_r in zip(h5_rlzs, oq_rlzs):
        assert h5_r.ordinal == oq_r.ordinal
        assert h5_r.source_path == oq_r.sm_lt_path
        assert h5_r.gsim_path == oq_r.gsim_lt_path


# ── disagg probe ─────────────────────────────────────────────────────────────


def test_disagg_shape_descr_and_extra(disagg_pair):
    """shape_descr identical to OQ Extractor; dict keys match OQ rlz labels (normalised format)."""
    reader, extractor, kind, imt = disagg_pair
    probe_h5_dict = reader.disagg_rlzs(kind)
    probe_h5 = next(iter(probe_h5_dict.values()))
    probe_oq = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')
    assert probe_h5.shape_descr == [str(d) for d in probe_oq.shape_descr]
    # OQ uses 'rlzN' (no hyphen, no padding); our keys are 'rlz-NNN'. Normalise OQ labels.
    n_rlz = len(probe_h5_dict)
    n_digits = max(3, len(str(n_rlz - 1)))
    oq_ordinals = [int(str(lbl)[3:]) for lbl in probe_oq.extra]
    expected_keys = [f'rlz-{o:0{n_digits}d}' for o in oq_ordinals]
    assert list(probe_h5_dict.keys()) == expected_keys


def test_disagg_bin_centres(disagg_pair):
    """Bin centres for every kind axis identical to OQ Extractor probe."""
    reader, extractor, kind, imt = disagg_pair
    probe_h5 = next(iter(reader.disagg_rlzs(kind).values()))
    probe_oq = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')
    for ax in kind.split('_'):
        ax_lo = ax.lower()
        h5_vals = getattr(probe_h5, ax_lo)
        oq_vals = getattr(probe_oq, ax_lo)
        oq_decoded = [v.decode() if isinstance(v, bytes) else v for v in oq_vals]
        h5_decoded = [v.decode() if isinstance(v, bytes) else v for v in h5_vals]
        # TRT-style axes are strings; numeric axes compare as floats.
        if isinstance(oq_decoded[0], str):
            assert h5_decoded == oq_decoded, f'bin labels mismatch for axis {ax}'
        else:
            assert np.allclose(h5_decoded, oq_decoded, rtol=1e-5), f'bin centres mismatch for axis {ax}'


def test_disagg_array_numerical_equality(disagg_pair):
    """Disagg probability array numerically identical to OQ Extractor probe (all rlzs)."""
    reader, extractor, kind, imt = disagg_pair
    probe_h5_dict = reader.disagg_rlzs(kind)
    probe_oq = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')
    # Reconstruct (*kind_bins, 1, 1, n_rlz) by stacking per-rlz arrays along the last axis.
    h5_arr = np.stack([e.array for e in probe_h5_dict.values()], axis=-1)
    assert np.allclose(h5_arr, probe_oq.array, rtol=1e-5), (
        f'disagg array mismatch: max abs diff = {np.max(np.abs(h5_arr - probe_oq.array)):.3e}'
    )


def test_bins_digest_exact_equality(disagg_pair):
    """compute_bins_digest produces the same 16-char hex string for both probes."""
    reader, extractor, kind, imt = disagg_pair
    probe_h5 = next(iter(reader.disagg_rlzs(kind).values()))
    probe_oq = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')
    digest_h5 = extract_disagg_hdf5.compute_bins_digest(probe_h5)
    digest_oq = extract_disagg_hdf5.compute_bins_digest(probe_oq)
    assert digest_h5 == digest_oq, f'bins_digest mismatch: {digest_h5!r} != {digest_oq!r}'


# ── End-to-end pipeline ───────────────────────────────────────────────────────


def test_disagg_pipeline_values_match_oq_reference(disagg_pair):
    """disaggs_to_record_batch_reader disagg_values and disagg_bins match OQ reference.

    Builds the disagg RecordBatch via our h5py pipeline and verifies every row's
    flattened probability array equals the same rlz's data from the OQ Extractor probe.
    """
    reader, extractor, kind, imt = disagg_pair

    h5_batches = list(
        extract_disagg_hdf5.disaggs_to_record_batch_reader(
            hdf5_file=str(_DISAGG_HDF5),
            calculation_id='compat-test',
            compatible_calc_id='compat-0',
            producer_digest='sha256:' + 'a' * 64,
            config_digest='cfg-compat',
            probability=ProbabilityEnum._2_PCT_IN_50YRS,
            hazard_model_id='COMPAT_TEST',
            target_aggr='mean',
            kind=kind,
        )
    )
    assert len(h5_batches) >= 1

    # Flatten per-rlz batches (one batch per rlz, 1 row each).
    rlz_col = [v for b in h5_batches for v in b.column('rlz').to_pylist()]
    vals_col = [v for b in h5_batches for v in b.column('disagg_values').to_pylist()]
    bins_rows = [v for b in h5_batches for v in b.column('disagg_bins').to_pylist()]

    # Build reference: {rlz_key: flattened_array} from OQ probe (keys in our 'rlz-NNN' format).
    probe_oq = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')
    # Squeeze imt/poe dims, move rlz to front.
    oq_arr = probe_oq.array  # (*kind_bins, imt=1, poe=1, n_rlz)
    oq_arr = np.squeeze(oq_arr, axis=tuple(i for i, s in enumerate(oq_arr.shape[:-1]) if s == 1))  # (*kind_bins, n_rlz)
    oq_arr = np.moveaxis(oq_arr, -1, 0)  # (n_rlz, *kind_bins)
    n_rlz = oq_arr.shape[0]
    # OQ uses 'rlzN'; normalise to our 'rlz-NNN' format for keying the reference dict.
    oq_ordinals = [int(str(lbl)[3:]) for lbl in probe_oq.extra]
    n_digits = max(3, len(str(max(oq_ordinals))))
    oq_ref = {f'rlz-{oq_ordinals[i]:0{n_digits}d}': oq_arr[i].ravel().astype(np.float32) for i in range(n_rlz)}

    # Compare per rlz.
    for rlz_label, row_vals in zip(rlz_col, vals_col):
        h5_vals = np.asarray(row_vals, dtype=np.float32)
        oq_vals = oq_ref[rlz_label]
        assert np.allclose(h5_vals, oq_vals, rtol=1e-5), (
            f'disagg_values mismatch for {rlz_label}: max abs diff = {np.max(np.abs(h5_vals - oq_vals)):.3e}'
        )

    # disagg_bins: axis names and bin-centre strings must be identical across all rows.
    probe_h5 = next(iter(reader.disagg_rlzs(kind).values()))
    for row_bins in bins_rows:
        for (ax_name, bin_strs), expected_ax in zip(
            row_bins,
            [ax.lower() for ax in kind.split('_')],
        ):
            assert ax_name == expected_ax
            expected_strs = extract_disagg_hdf5._stringify_bin_centers(getattr(probe_h5, ax_name))
            assert bin_strs == expected_strs, f'bin strings mismatch for axis {ax_name}'
