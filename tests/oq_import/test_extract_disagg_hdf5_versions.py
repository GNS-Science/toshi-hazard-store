"""Cross-version compatibility test for disaggregation extraction.

Drives disaggs_to_record_batch_reader against the committed fixture HDF5 and
compares structural and numeric summaries against a committed baseline.  Run via
the tox OQ-version matrix (py311-oq{3201,3210,...}) so each env exercises a
different openquake-engine install.

Capture / regenerate the baseline:
    THS_REGEN_DISAGG_BASELINE=1 uv run tox -e py311-oq3251

Then run the full matrix:
    uv run tox -e py311-oq3201,py311-oq3210,py311-oq3221,py311-oq3234,py311-oq3241,py311-oq3251
"""

import json
import os
from pathlib import Path

import numpy as np
import pytest

try:
    import openquake  # noqa

    HAVE_OQ = True
except ImportError:
    HAVE_OQ = False

if HAVE_OQ:
    pass  # Extractor imported inside functions that need it to keep the guard clean

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.pyarrow.dataset_schema import get_disagg_realisation_schema
from toshi_hazard_store.model.revision_4 import extract_disagg_hdf5

_DISAGG_HDF5_PATH = (
    Path(__file__).parent.parent
    / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTI4NDUy/calc_1.hdf5'
)

BASELINE_PATH = Path(__file__).parent / 'baselines/disagg_values_summary.json'

_HAZARD_MODEL_ID = 'TEST_MODEL_v0'
_TARGET_AGGR = 'mean'

# OQ version range this test is designed for.  Runs under an unexpected OQ
# version are skipped rather than silently producing mis-attributed diffs.
_OQ_MIN = (3, 20, 1)
_OQ_MAX = (3, 25, 99)

_REQUIRE_OQ = pytest.mark.skipif(not HAVE_OQ, reason="openquake not installed")


def _oq_version_tuple():
    if not HAVE_OQ:
        return (0, 0, 0)
    try:
        from openquake.baselib import __version__ as _v  # version lives in baselib, not the top package
        raw = _v
    except Exception:
        raw = '0.0.0'
    parts = str(raw).split('.')[:3]
    return tuple(int(p) for p in parts)


def _check_oq_version():
    """Skip the test when the installed OQ version is outside the matrix range."""
    v = _oq_version_tuple()
    if v < _OQ_MIN or v > _OQ_MAX:
        pytest.skip(f'openquake {".".join(str(x) for x in v)} outside tested range '
                    f'{".".join(str(x) for x in _OQ_MIN)}–{".".join(str(x) for x in _OQ_MAX[:2])}')


def _build_summary(reader) -> dict:
    """Extract structural and numeric summary from a RecordBatchReader."""
    all_batches = list(reader)
    total_rows = sum(b.num_rows for b in all_batches)

    first_batch = all_batches[0]
    first_bins = first_batch.column('disagg_bins')[0].as_py()  # list of (key, value) pairs
    axes = [k for k, _ in first_bins]
    per_axis_bin_counts = [len(v) for _, v in first_bins]
    n_cells_per_rlz = len(first_batch.column('disagg_values')[0])

    totals = []
    mins = []
    maxs = []
    for batch in all_batches:
        values_col = batch.column('disagg_values')
        for i in range(batch.num_rows):
            row = np.asarray(values_col[i].as_py(), dtype=np.float64)
            totals.append(float(row.sum()))
            mins.append(float(row.min()))
            maxs.append(float(row.max()))

    return {
        'axes': axes,
        'n_rlz': total_rows,
        'n_cells_per_rlz': n_cells_per_rlz,
        'per_axis_bin_counts': per_axis_bin_counts,
        'totals_per_rlz_sorted': sorted(totals),
        'min_per_rlz_sorted': sorted(mins),
        'max_per_rlz_sorted': sorted(maxs),
    }


@_REQUIRE_OQ
def test_cross_version_compatibility():
    """Schema, structure and numeric summaries are stable across OQ versions.

    On each run the installed OQ version is reported in the test output; the
    assertion compares against the committed baseline produced by OQ 3.25.1.
    """
    _check_oq_version()

    if not _DISAGG_HDF5_PATH.exists():
        pytest.skip(f'disagg fixture not found: {_DISAGG_HDF5_PATH}')

    import json as _json

    oqv = '.'.join(str(x) for x in _oq_version_tuple())
    print(f'\n[OQ {oqv}] reading fixture {_DISAGG_HDF5_PATH.name}')

    # Resolve kind from the fixture itself so the test stays fixture-agnostic.
    from openquake.calculators.extract import Extractor

    oqp = _json.loads(Extractor(str(_DISAGG_HDF5_PATH)).get('oqparam').json)
    kinds = oqp.get('disagg_outputs', [])
    kind = next((k for k in kinds if 'Mag' in k and 'Dist' in k), kinds[0])

    reader = extract_disagg_hdf5.disaggs_to_record_batch_reader(
        hdf5_file=str(_DISAGG_HDF5_PATH),
        calculation_id='test-calc-id',
        compatible_calc_id='compat-0',
        producer_digest='sha256:' + 'a' * 64,
        config_digest='cfg-abc123',
        probability=ProbabilityEnum._2_PCT_IN_50YRS,
        hazard_model_id=_HAZARD_MODEL_ID,
        target_aggr=_TARGET_AGGR,
        kind=kind,
    )

    # Schema must be exact regardless of OQ version.
    expected_schema = get_disagg_realisation_schema()
    assert reader.schema.equals(expected_schema), (
        f'[OQ {oqv}] schema mismatch:\n  got:      {reader.schema}\n'
        f'  expected: {expected_schema}'
    )

    try:
        summary = _build_summary(reader)
    except ValueError as exc:
        if 'squeeze' in str(exc):
            pytest.fail(
                f'[OQ {oqv}] disagg extraction failed with a squeeze error.\n'
                f'OQ <3.24 uses an older spec=rlzs convention where the rlz count appears\n'
                f'in the poe axis rather than as a separate trailing dimension.\n'
                f'The code in generate_disagg_record_batches requires OQ >=3.24.\n'
                f'Original error: {exc}'
            )
        raise
    print(f'[OQ {oqv}] summary: n_rlz={summary["n_rlz"]}, axes={summary["axes"]}, '
          f'n_cells={summary["n_cells_per_rlz"]}')

    # Baseline capture / regenerate mode.
    if os.environ.get('THS_REGEN_DISAGG_BASELINE') == '1':
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True))
        pytest.skip(f'[OQ {oqv}] baseline written to {BASELINE_PATH}')

    # Normal mode: load and compare.
    if not BASELINE_PATH.exists():
        pytest.fail(
            f'Baseline not found at {BASELINE_PATH}. '
            'Capture it first: THS_REGEN_DISAGG_BASELINE=1 uv run tox -e py311-oq3251'
        )

    baseline = json.loads(BASELINE_PATH.read_text())

    # Structural fields — exact match.
    assert summary['axes'] == baseline['axes'], (
        f'[OQ {oqv}] axes changed: got {summary["axes"]}, expected {baseline["axes"]}'
    )
    assert summary['n_rlz'] == baseline['n_rlz'], (
        f'[OQ {oqv}] n_rlz changed: got {summary["n_rlz"]}, expected {baseline["n_rlz"]}'
    )
    assert summary['n_cells_per_rlz'] == baseline['n_cells_per_rlz'], (
        f'[OQ {oqv}] n_cells_per_rlz changed: got {summary["n_cells_per_rlz"]}, '
        f'expected {baseline["n_cells_per_rlz"]}'
    )
    assert summary['per_axis_bin_counts'] == baseline['per_axis_bin_counts'], (
        f'[OQ {oqv}] per_axis_bin_counts changed: got {summary["per_axis_bin_counts"]}, '
        f'expected {baseline["per_axis_bin_counts"]}'
    )

    # Numeric fields — within tolerance (sorted so rlz-reordering across OQ versions is harmless).
    rtol, atol = 1e-2, 1e-12
    for field in ('totals_per_rlz_sorted', 'min_per_rlz_sorted', 'max_per_rlz_sorted'):
        got = np.asarray(summary[field])
        exp = np.asarray(baseline[field])
        if not np.allclose(got, exp, rtol=rtol, atol=atol):
            max_diff = float(np.max(np.abs(got - exp)))
            rel_diff = float(np.max(np.abs((got - exp) / (np.abs(exp) + atol))))
            pytest.fail(
                f'[OQ {oqv}] {field} exceeds tolerance (rtol={rtol}):\n'
                f'  max abs diff = {max_diff:.3e}, max rel diff = {rel_diff:.3e}'
            )

    print(f'[OQ {oqv}] all assertions passed')
