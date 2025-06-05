import json
from pathlib import Path

import pyarrow.dataset as ds
import pytest
from nzshm_common.location import location

try:
    import openquake  # noqa

    HAVE_OQ = True
except ImportError:
    HAVE_OQ = False

if HAVE_OQ:
    from openquake.calculators.extract import Extractor

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.model.revision_4 import extract_classical_hdf5
from toshi_hazard_store.oq_import.parse_oq_realizations import build_rlz_gmm_map, build_rlz_source_map
from toshi_hazard_store.oq_import.transform import parse_logic_tree_branches


def build_maps(hdf5_file):
    extractor = Extractor(str(hdf5_file))
    # oqparam = json.loads(extractor.get('oqparam').json)
    source_lt, gsim_lt, rlz_lt = parse_logic_tree_branches(extractor)

    # check gsims
    build_rlz_gmm_map(gsim_lt)
    # check sources
    try:
        build_rlz_source_map(source_lt)
    except KeyError as exc:
        print(exc)
        raise
        # return False
    return True


# @pytest.mark.skip('fixtures not checked in')
def test_logic_tree_registry_lookup():
    good_file = (
        Path(__file__).parent.parent
        / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
    )
    assert build_maps(good_file)


@pytest.mark.skip('fixtures not checked in')
def test_logic_tree_registry_lookup_bad_examples():

    disagg = Path('/GNSDATA/LIB/toshi-hazard-store/WORKING/DISAGG')
    bad_file_1 = disagg / 'calc_1.hdf5'
    # bad_file_2 = disagg / 'openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazoxMDYzMzU3' / 'calc_1.hdf5'
    bad_file_3 = disagg / 'openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTI2MTg2' / 'calc_1.hdf5'
    bad_file_4 = disagg / 'openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazoxMzU5MTQ1' / 'calc_1.hdf5'

    # first subtask of first gt in gt_index
    # >>> ValueError: Unknown GSIM: ParkerEtAl2021SInter
    # T3BlbnF1YWtlSGF6YXJkVGFzazoxMzU5MTQ1 from  R2VuZXJhbFRhc2s6MTM1OTEyNQ==
    #
    # Created: April 3rd, 2023 at 3:42:21 PM GMT+12
    # Description: hazard ID: NSHM_v1.0.4, hazard aggregation target: mean
    #
    # raises KeyError: 'disaggregation sources'

    with pytest.raises(KeyError) as exc_info:
        build_maps(bad_file_4)
    assert 'disaggregation sources' in str(exc_info)

    # first subtask of last gt in gt_index
    # T3BlbnF1YWtlSGF6YXJkVGFzazo2OTI2MTg2 from R2VuZXJhbFRhc2s6NjkwMTk2Mw==
    #
    # Created: March 22nd, 2024 at 11:51:20 AM GMT+13
    # Description: Disaggregation NSHM_v1.0.4
    #
    # raises KeyError: '[dm0.7, bN[0.902, 4.6], C4.0, s0.28]'
    """
    >>> args = gt_index['R2VuZXJhbFRhc2s6NjkwMTk2Mw==']['arguments']
    """
    with pytest.raises(KeyError) as exc_info:
        build_maps(bad_file_3)
    assert '[dm0.7, bN[0.902, 4.6], C4.0, s0.28]' in str(exc_info)

    # 2nd random choice (weird setup) ++ ValueError: Unknown GSIM: ParkerEtAl2021SInter
    # T3BlbnF1YWtlSGF6YXJkVGFzazoxMDYzMzU3 from ??
    # Created: February 2nd, 2023 at 9:22:36 AM GMT+13
    # raises KeyError: 'disaggregation sources'

    # with pytest.raises(KeyError) as exc_info:
    #     build_maps(bad_file_2)
    # assert 'disaggregation sources' in str(exc_info)

    # first random choice
    # raises KeyError: '[dmTL, bN[0.95, 16.5], C4.0, s0.42]'
    with pytest.raises(KeyError) as exc_info:
        build_maps(bad_file_1)
    assert '[dmTL, bN[0.95, 16.5], C4.0, s0.42]' in str(exc_info)


@pytest.mark.skipif(not HAVE_OQ, reason="Test fails if openquake is not installed")
def test_realisation_batches_from_hdf5(tmp_path):

    hdf5_fixture = (
        Path(__file__).parent.parent
        / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
    )

    extractor = Extractor(str(hdf5_fixture))
    oqparam = json.loads(extractor.get('oqparam').json)
    assert oqparam['calculation_mode'] == 'classical', "calculation_mode is not 'classical'"
    vs30 = int(oqparam['reference_vs30_value'])
    oq = extractor.dstore['oqparam']  # old skool way
    imtl_keys = sorted(list(oq.imtls.keys()))

    batches = list(extract_classical_hdf5.generate_rlz_record_batches(extractor, vs30, imtl_keys, 'A', 'B', 'C', 'D'))
    assert len(batches) == 12


@pytest.mark.skipif(not HAVE_OQ, reason="Test fails if openquake is not installed")
def test_hdf5_realisations_direct_to_parquet_roundtrip(tmp_path):

    hdf5_fixture = (
        Path(__file__).parent.parent
        / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
    )

    # hdf5_fixture = Path(__file__).parent.parent / 'fixtures' / 'oq_import' / 'calc_9.hdf5'

    model_generator = extract_classical_hdf5.rlzs_to_record_batch_reader(
        str(hdf5_fixture),
        calculation_id="dummy_calc_id",
        compatible_calc_id="CCFK",
        producer_digest="PCFK",
        config_digest="CCFFFG",
    )

    print(model_generator)

    # now write out to parquet and validate
    output_folder = tmp_path / "ds_direct"

    # write the dataset
    pyarrow_dataset.append_models_to_dataset(model_generator, str(output_folder))

    # read and check the dataset
    dataset = ds.dataset(output_folder, format='parquet', partitioning='hive')
    table = dataset.to_table()
    df = table.to_pandas()

    print(df)
    print(df.shape)
    print(df.tail())
    print(df.info())
    assert df.shape == (192, 12)

    test_loc = location.get_locations(['CHC'])[0]

    test_loc_df = df[df['nloc_001'] == test_loc.code]
    print(test_loc_df[['nloc_001', 'nloc_0', 'imt', 'rlz', 'vs30', 'sources_digest', 'gmms_digest']])  # 'rlz_key'
    # print(test_loc_df.tail())

    assert test_loc_df.shape == (192 / 4, 12)
    assert test_loc_df['imt'].tolist()[0] == 'PGA'
    assert (
        test_loc_df['imt'].tolist()[-1] == 'SA(3.0)'
    ), "not so weird, as the IMT keys are sorted alphnumerically in openquake now."
    assert (
        test_loc_df['imt'].tolist().index('SA(3.0)') == 3
    ), "also not so weird, as the IMT keys are sorted alphnumerically"

    assert test_loc_df['nloc_001'].tolist()[0] == test_loc.code
    assert test_loc_df['nloc_0'].tolist()[0] == test_loc.resample(1.0).code
