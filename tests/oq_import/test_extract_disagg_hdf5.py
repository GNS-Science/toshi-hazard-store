"""Tests for disaggregation extraction from OpenQuake HDF5 files.

Requires an OpenQuake disaggregation HDF5 file at the committed fixture path.
Tests are skipped when OpenQuake is not installed.
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

_DISAGG_HDF5_PATH = (
    Path(__file__).parent.parent
    / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTI4NDUy/calc_1.hdf5'
)

_REQUIRE_OQ = pytest.mark.skipif(not HAVE_OQ, reason="openquake not installed")


@pytest.fixture(scope='module')
def disagg_hdf5_info():
    """Return (path, kind, imts) for the committed disagg fixture."""
    oqp = json.loads(Extractor(str(_DISAGG_HDF5_PATH)).get('oqparam').json)
    imts = list(oqp['iml_disagg'].keys())
    kinds = oqp['disagg_outputs']
    kind = next((k for k in kinds if 'Mag' in k and 'Dist' in k), kinds[0])
    return _DISAGG_HDF5_PATH, kind, imts


@pytest.fixture(scope='module')
def probability():
    return ProbabilityEnum._2_PCT_IN_50YRS


@_REQUIRE_OQ
def test_compute_bins_digest_deterministic(disagg_hdf5_info):
    """compute_bins_digest returns the same value on repeated calls."""
    hdf5_path, kind, imts = disagg_hdf5_info
    extractor = Extractor(str(hdf5_path))
    probe = extractor.get(f'disagg?kind={kind}&imt={imts[0]}&site_id=0&poe_id=0&spec=rlzs')
    digest1 = extract_disagg_hdf5.compute_bins_digest(probe)
    digest2 = extract_disagg_hdf5.compute_bins_digest(probe)
    assert digest1 == digest2
    assert len(digest1) == 16


@_REQUIRE_OQ
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


@_REQUIRE_OQ
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


@_REQUIRE_OQ
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


@_REQUIRE_OQ
def test_disagg_axes_column_populated(disagg_hdf5_info, probability):
    """Every row carries the same axis-order list matching the HDF5 shape_descr."""
    hdf5_path, kind, imts = disagg_hdf5_info
    extractor = Extractor(str(hdf5_path))
    probe = extractor.get(f'disagg?kind={kind}&imt={imts[0]}&site_id=0&poe_id=0&spec=rlzs')
    expected_axes = [str(d) for d in probe.shape_descr if d not in ('imt', 'poe')]

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
        axes_col = batch.column('disagg_axes')
        assert batch.num_rows > 0
        for i in range(batch.num_rows):
            assert axes_col[i].as_py() == expected_axes


@_REQUIRE_OQ
def test_record_count_matches_shape(disagg_hdf5_info, probability):
    """Total rows == n_sites * n_rlz; each row's disagg_values has product(dim_sizes) entries."""
    hdf5_path, kind, imts = disagg_hdf5_info
    extractor = Extractor(str(hdf5_path))

    # Determine expected shape from a probe.
    probe = extractor.get(f'disagg?kind={kind}&imt={imts[0]}&site_id=0&poe_id=0&spec=rlzs')
    n_rlz = len(probe.extra)
    n_cells_per_rlz = probe.array.size // n_rlz

    sitecol_df = extractor.get('sitecol').to_dframe()
    n_sites = sitecol_df.shape[0]

    expected_rows = n_sites * n_rlz

    reader = extract_disagg_hdf5.disaggs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id='test-calc-id',
        compatible_calc_id='compat-0',
        producer_digest='sha256:' + 'a' * 64,
        config_digest='cfg-abc123',
        probability=probability,
        kind=kind,
    )
    total_rows = 0
    for batch in reader:
        total_rows += batch.num_rows
        values_col = batch.column('disagg_values')
        axes_col = batch.column('disagg_axes')
        for i in range(batch.num_rows):
            assert len(values_col[i]) == n_cells_per_rlz
            # Cross-check: product of per-axis bin counts equals the flattened length.
            axes_i = axes_col[i].as_py()
            expected_len = 1
            for ax in axes_i:
                expected_len *= len(getattr(probe, ax))
            assert expected_len == n_cells_per_rlz
    assert total_rows == expected_rows


@_REQUIRE_OQ
def test_wrong_calculation_mode_raises(disagg_hdf5_info, probability):
    """Reader raises ValueError when the HDF5 is not a disaggregation calc."""
    hdf5_path, kind, _ = disagg_hdf5_info
    # Use the classical fixture from the oq_import suite if it exists.
    classical_path = (
        Path(__file__).parent.parent
        / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
    )
    if not classical_path.exists():
        pytest.skip("classical fixture not present")
    with pytest.raises(ValueError, match="disaggregation"):
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


@_REQUIRE_OQ
def test_invalid_kind_raises(disagg_hdf5_info, probability):
    """Reader raises ValueError when the requested kind is not in the HDF5."""
    hdf5_path, kind, _ = disagg_hdf5_info
    with pytest.raises(ValueError, match="not in disagg_outputs"):
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
