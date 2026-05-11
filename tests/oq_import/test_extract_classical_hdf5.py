import dataclasses
import json
from pathlib import Path

import pyarrow.dataset as ds
import pytest
from nzshm_common.location import location

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.model.revision_4 import extract_classical_hdf5
from toshi_hazard_store.oq_import.h5py_reader import OqHdf5Reader
from toshi_hazard_store.oq_import.parse_oq_realizations import build_rlz_gmm_map, build_rlz_mapper, build_rlz_source_map
from toshi_hazard_store.oq_import.transform import parse_logic_tree_branches

_CLASSICAL_HDF5_PATH = (
    Path(__file__).parent.parent
    / 'fixtures/oq_import/openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTMxODkz/calc_1.hdf5'
)


def build_maps(hdf5_file):
    reader = OqHdf5Reader(str(hdf5_file))
    source_lt, gsim_lt, rlz_lt = parse_logic_tree_branches(reader)

    # check gsims
    build_rlz_gmm_map(gsim_lt)
    # check sources
    try:
        build_rlz_source_map(source_lt)
    except KeyError as exc:
        print(exc)
        raise
    return True


def test_rlz_mapper():
    # we have to jump through a few hoops to serialize/deserialize the realization mapper
    def to_dict(rlz_mapper):
        rlz_mapper_dict = {}
        for ind, rlz_record in rlz_mapper.items():
            rlz_record_dict = rlz_record._asdict()
            for k, v in rlz_record_dict.items():
                if dataclasses.is_dataclass(v):
                    rlz_record_dict[k] = dataclasses.asdict(v)
            rlz_mapper_dict[str(ind)] = rlz_record_dict
        return rlz_mapper_dict

    rlz_mapper_file = Path(__file__).parent.parent / 'fixtures/oq_import/rlz_mapper.json'
    reader = OqHdf5Reader(str(_CLASSICAL_HDF5_PATH))
    rlz_mapper = build_rlz_mapper(reader)
    rlz_mapper_dict = to_dict(rlz_mapper)
    expected = json.loads(rlz_mapper_file.read_text())
    # expected was built with empty strings instead of None as `extra` member for gmm branches, but
    # we build our BranchRegistryEntry objects on the fly with None.
    for value in expected.values():
        if value['gmms']['extra'] == '':
            value['gmms']['extra'] = None
    assert rlz_mapper_dict == expected


# @pytest.mark.skip('fixtures not checked in')
def test_logic_tree_registry_lookup():
    assert build_maps(_CLASSICAL_HDF5_PATH)


@pytest.mark.skip('fixtures not checked in')
def test_logic_tree_registry_lookup_bad_examples():

    disagg = Path('/GNSDATA/LIB/toshi-hazard-store/WORKING/DISAGG')
    bad_file_1 = disagg / 'calc_1.hdf5'
    bad_file_3 = disagg / 'openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazo2OTI2MTg2' / 'calc_1.hdf5'
    bad_file_4 = disagg / 'openquake_hdf5_archive-T3BlbnF1YWtlSGF6YXJkVGFzazoxMzU5MTQ1' / 'calc_1.hdf5'

    with pytest.raises(KeyError) as exc_info:
        build_maps(bad_file_4)
    assert 'disaggregation sources' in str(exc_info)

    with pytest.raises(KeyError) as exc_info:
        build_maps(bad_file_3)
    assert '[dm0.7, bN[0.902, 4.6], C4.0, s0.28]' in str(exc_info)

    with pytest.raises(KeyError) as exc_info:
        build_maps(bad_file_1)
    assert '[dmTL, bN[0.95, 16.5], C4.0, s0.42]' in str(exc_info)


def test_realisation_batches_from_hdf5(tmp_path):
    reader = OqHdf5Reader(str(_CLASSICAL_HDF5_PATH))
    oqparam = reader.oqparam()
    assert oqparam['calculation_mode'] == 'classical', "calculation_mode is not 'classical'"
    hazard_imtls = oqparam.get('hazard_imtls') or oqparam.get('intensity_measure_types_and_levels', {})
    imtl_keys = sorted(list(hazard_imtls.keys()))

    batches = list(extract_classical_hdf5.generate_rlz_record_batches(reader, imtl_keys, 'A', 'B', 'C', 'D'))
    assert len(batches) == 12


def test_hdf5_realisations_direct_to_parquet_roundtrip(tmp_path):

    model_generator = extract_classical_hdf5.rlzs_to_record_batch_reader(
        str(_CLASSICAL_HDF5_PATH),
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
    print(test_loc_df[['nloc_001', 'nloc_0', 'imt', 'rlz', 'vs30', 'sources_digest', 'gmms_digest']])

    assert test_loc_df.shape == (192 / 4, 12)
    assert test_loc_df['imt'].tolist()[0] == 'PGA'
    assert test_loc_df['imt'].tolist()[-1] == 'SA(3.0)', (
        "not so weird, as the IMT keys are sorted alphnumerically in openquake now."
    )
    assert test_loc_df['imt'].tolist().index('SA(3.0)') == 3, (
        "also not so weird, as the IMT keys are sorted alphnumerically"
    )

    assert test_loc_df['nloc_001'].tolist()[0] == test_loc.code
    assert test_loc_df['nloc_0'].tolist()[0] == test_loc.resample(1.0).code
