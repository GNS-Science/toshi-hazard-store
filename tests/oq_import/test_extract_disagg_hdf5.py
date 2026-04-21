"""Tests for disaggregation extraction from OpenQuake HDF5 files.

Requires an OpenQuake disaggregation HDF5 file at DISAGG_HDF5_PATH (see fixture below).
Tests are skipped when OpenQuake is not installed or the fixture file is absent.
"""

import json
from pathlib import Path

import pytest

try:
    import openquake  # noqa

    HAVE_OQ = True
except ImportError:
    HAVE_OQ = False

if HAVE_OQ:
    from openquake.calculators.extract import Extractor

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.pyarrow.dataset_schema import get_disagg_realisation_schema
from toshi_hazard_store.model.revision_4 import extract_disagg_hdf5

# Try the repo-root calc_1.hdf5 first (newer format, used in development), fall back to committed fixture.
_REPO_ROOT = Path(__file__).parent.parent.parent
_CANDIDATE_PATHS = [
    _REPO_ROOT / 'calc_1.hdf5',
    _REPO_ROOT / 'tests/fixtures/disaggregation/calc_1.hdf5',
]


def _find_disagg_hdf5():
    """Return the first disaggregation HDF5 fixture that is present and is new-format."""
    if not HAVE_OQ:
        return None
    for p in _CANDIDATE_PATHS:
        if not p.exists():
            continue
        try:
            extractor = Extractor(str(p))
            oqp = json.loads(extractor.get('oqparam').json)
            if oqp.get('calculation_mode') != 'disaggregation':
                continue
            # Probe extraction to check the format is compatible with the current OQ extractor.
            imts = list(oqp.get('iml_disagg', {}).keys())
            kinds = oqp.get('disagg_outputs', [])
            kind = next((k for k in kinds if 'Mag' in k and 'Dist' in k), kinds[0] if kinds else None)
            if imts and kind:
                extractor.get(f'disagg?kind={kind}&imt={imts[0]}&site_id=0&poe_id=0&spec=rlzs')
                return p, kind, imts
        except Exception:
            continue
    return None


_FIXTURE_INFO = _find_disagg_hdf5()

_REQUIRE_OQ_AND_FIXTURE = pytest.mark.skipif(
    not HAVE_OQ or _FIXTURE_INFO is None,
    reason="openquake not installed or no compatible disagg HDF5 fixture found",
)


@pytest.fixture(scope='module')
def disagg_hdf5_info():
    """Return (path, kind, imts) for the available disagg fixture."""
    assert _FIXTURE_INFO is not None
    return _FIXTURE_INFO


@pytest.fixture(scope='module')
def probability():
    return ProbabilityEnum._2_PCT_IN_50YRS


@_REQUIRE_OQ_AND_FIXTURE
def test_compute_bins_digest_deterministic(disagg_hdf5_info):
    """compute_bins_digest returns the same value on repeated calls."""
    hdf5_path, kind, imts = disagg_hdf5_info
    extractor = Extractor(str(hdf5_path))
    probe = extractor.get(f'disagg?kind={kind}&imt={imts[0]}&site_id=0&poe_id=0&spec=rlzs')
    digest1 = extract_disagg_hdf5.compute_bins_digest(probe)
    digest2 = extract_disagg_hdf5.compute_bins_digest(probe)
    assert digest1 == digest2
    assert len(digest1) == 16


@_REQUIRE_OQ_AND_FIXTURE
def test_disaggs_to_record_batch_reader_smoke(disagg_hdf5_info, probability, tmp_path):
    """Reader yields at least one batch conforming to the disagg schema."""
    hdf5_path, kind, imts = disagg_hdf5_info
    reader = extract_disagg_hdf5.disaggs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id='test-calc-id',
        compatible_calc_id='compat-0',
        producer_digest='sha256:' + 'a' * 64,
        config_digest='cfg-abc123',
        probability=probability,
        kind=kind,
    )
    expected_schema = get_disagg_realisation_schema()
    assert reader.schema.equals(expected_schema)

    batches = list(reader)
    assert len(batches) >= 1
    for batch in batches:
        assert batch.schema.equals(expected_schema)
        assert batch.num_rows > 0


@_REQUIRE_OQ_AND_FIXTURE
def test_probability_column_populated(disagg_hdf5_info, probability):
    """Every row carries the user-supplied probability name."""
    hdf5_path, kind, imts = disagg_hdf5_info
    reader = extract_disagg_hdf5.disaggs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id='test-calc-id',
        compatible_calc_id='compat-0',
        producer_digest='sha256:' + 'a' * 64,
        config_digest='cfg-abc123',
        probability=probability,
        kind=kind,
    )
    for batch in reader:
        prob_col = batch.column('probability')
        unique_probs = prob_col.dictionary.to_pylist()
        assert unique_probs == [probability.name]


@_REQUIRE_OQ_AND_FIXTURE
def test_kind_column_populated(disagg_hdf5_info, probability):
    """Every row carries the requested kind."""
    hdf5_path, kind, imts = disagg_hdf5_info
    reader = extract_disagg_hdf5.disaggs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id='test-calc-id',
        compatible_calc_id='compat-0',
        producer_digest='sha256:' + 'a' * 64,
        config_digest='cfg-abc123',
        probability=probability,
        kind=kind,
    )
    for batch in reader:
        kind_col = batch.column('kind')
        unique_kinds = kind_col.dictionary.to_pylist()
        assert unique_kinds == [kind]


@_REQUIRE_OQ_AND_FIXTURE
def test_record_count_matches_shape(disagg_hdf5_info, probability):
    """Total rows == n_sites * n_imts * product(dim_sizes) * n_rlz."""
    hdf5_path, kind, imts = disagg_hdf5_info
    extractor = Extractor(str(hdf5_path))

    # Determine expected shape from a probe.
    probe = extractor.get(f'disagg?kind={kind}&imt={imts[0]}&site_id=0&poe_id=0&spec=rlzs')
    n_rlz = len(probe.extra)
    n_cells_per_imt_site = probe.array.size // n_rlz  # excludes rlz dim

    sitecol_df = extractor.get('sitecol').to_dframe()
    n_sites = sitecol_df.shape[0]
    n_imts = len(imts)

    expected_total = n_sites * n_imts * n_cells_per_imt_site * n_rlz

    reader = extract_disagg_hdf5.disaggs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id='test-calc-id',
        compatible_calc_id='compat-0',
        producer_digest='sha256:' + 'a' * 64,
        config_digest='cfg-abc123',
        probability=probability,
        kind=kind,
    )
    total_rows = sum(batch.num_rows for batch in reader)
    assert total_rows == expected_total


@_REQUIRE_OQ_AND_FIXTURE
def test_wrong_calculation_mode_raises(disagg_hdf5_info, probability):
    """Reader raises AssertionError when the HDF5 is not a disaggregation calc."""
    hdf5_path, kind, _ = disagg_hdf5_info
    # Use the classical fixture from the oq_import suite if it exists.
    classical_path = (
        Path(__file__).parent.parent
        / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
    )
    if not classical_path.exists():
        pytest.skip("classical fixture not present")
    with pytest.raises(AssertionError, match="disaggregation"):
        list(
            extract_disagg_hdf5.disaggs_to_record_batch_reader(
                hdf5_file=str(classical_path),
                calculation_id='x',
                compatible_calc_id='x',
                producer_digest='sha256:' + 'a' * 64,
                config_digest='x',
                probability=probability,
                kind=kind,
            )
        )


@_REQUIRE_OQ_AND_FIXTURE
def test_invalid_kind_raises(disagg_hdf5_info, probability):
    """Reader raises AssertionError when the requested kind is not in the HDF5."""
    hdf5_path, kind, _ = disagg_hdf5_info
    with pytest.raises(AssertionError, match="not in disagg_outputs"):
        list(
            extract_disagg_hdf5.disaggs_to_record_batch_reader(
                hdf5_file=str(hdf5_path),
                calculation_id='x',
                compatible_calc_id='x',
                producer_digest='sha256:' + 'a' * 64,
                config_digest='x',
                probability=probability,
                kind='Not_A_Real_Kind',
            )
        )
