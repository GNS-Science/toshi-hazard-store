"""
Basic model migration, structure
"""

import itertools

import pyarrow as pa
import pyarrow.dataset as ds
import pytest
from moto import mock_dynamodb
from pyarrow import fs

from toshi_hazard_store.model import drop_r4, migrate_r4
from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve
from toshi_hazard_store.model.pyarrow import pyarrow_aggr_dataset
from toshi_hazard_store.model.revision_4 import hazard_aggregate_curve


@pytest.fixture(scope='function')
def generate_rev4_aggregation_models(many_rlz_args):
    def model_generator():
        values = list(map(lambda x: x / 1e6, range(1, 51)))
        for loc, vs30, imt, agg in itertools.product(
            many_rlz_args["locs"][:5], many_rlz_args["vs30s"], many_rlz_args["imts"], ['mean', 'cov', '0.95']
        ):
            yield hazard_aggregate_curve.HazardAggregateCurve(
                compatible_calc_fk=("A", "AA"),
                hazard_model_id="NSHM_DUMMY_MODEL",
                values=values,
                imt=imt,
                vs30=vs30,
                agg=agg,
            ).set_location(loc)

    yield model_generator


@mock_dynamodb
class TestRevisionFourModelCreation_PynamoDB:

    def test_tables_exists(self, adapted_model):
        migrate_r4()
        assert adapted_model.CompatibleHazardCalculation.exists()
        assert adapted_model.HazardCurveProducerConfig.exists()
        assert adapted_model.HazardRealizationCurve.exists()
        drop_r4()


class TestRevisionFourModelCreation_WithAdaption:

    def test_CompatibleHazardCalculation_table_exists(self, adapted_model):
        print(adapted_model.CompatibleHazardCalculation)
        assert adapted_model.CompatibleHazardCalculation.exists()

    def test_HazardCurveProducerConfig_table_exists(self, adapted_model):
        print(adapted_model.HazardCurveProducerConfig)
        assert adapted_model.HazardCurveProducerConfig.exists()

    def test_HazardRealizationCurve_table_exists(self, adapted_model):
        print(adapted_model.HazardRealizationCurve)
        assert adapted_model.HazardRealizationCurve.exists()

    def test_CompatibleHazardCalculation_table_save_get(self, adapted_model):
        mCHC = adapted_model.CompatibleHazardCalculation
        m = mCHC(partition_key='A', uniq_id="AAA", notes='hello world')
        m.save()
        res = next(mCHC.query('A', mCHC.uniq_id == "AAA"))
        assert res.partition_key == "A"
        assert res.uniq_id == "AAA"
        assert res.notes == m.notes

    def test_HazardCurveProducerConfig_table_save_get(self, adapted_model):
        mHCPC = adapted_model.HazardCurveProducerConfig
        m = mHCPC(
            partition_key='A',
            range_key="openquake:3.16:#hashcode#",  # combination of the unique configuration identifiers
            compatible_calc_fk=(
                "A",
                "AA",
            ),  # must map to a valid CompatibleHazardCalculation.uniq_id (maybe wrap in transaction)
            producer_software='openquake',  # needs to be a long-lived, immutable ref
            producer_version_id='3.16',  # could also be a git rev
            configuration_hash='#hashcode#',
            configuration_data=None,
            notes='the original NSHM_v1.0.4 producer',
            imts=['PGA', 'SA(0.5)'],
            imt_levels=list(map(lambda x: x / 1e3, range(1, 51))),
        )
        m.save()
        assert m.version == 1

        res = next(
            mHCPC.query(
                'A',
                mHCPC.range_key == "openquake:3.16:#hashcode#",
                mHCPC.compatible_calc_fk == ("A", "AA"),  # filter_condition
            )
        )
        assert res.partition_key == "A"
        assert res.range_key == m.range_key
        assert res.notes == m.notes
        assert res.producer_software == m.producer_software
        assert res.version == 1

    def test_HazardRealizationCurve_table_save_get(self, adapted_model, generate_rev4_rlz_models):

        m = next(generate_rev4_rlz_models())
        print(m)
        mHRC = adapted_model.HazardRealizationCurve
        m.save()
        res = next(
            mHRC.query(
                m.partition_key,
                mHRC.sort_key == m.sort_key,
                # (mHRC.compatible_calc_fk == m.compatible_calc_fk)
                # & (mHRC.producer_config_fk == m.producer_config_fk)
                # & (mHRC.vs30 == m.vs30),  # filter_condition
            )
        )

        print(res)
        assert res.created.timestamp() == int(m.created.timestamp())  # approx
        assert res.vs30 == m.vs30
        assert res.imt == m.imt
        # assert res.values[0] == m.values[0]
        assert res.sort_key == '-38.160~178.247:0250:PGA:A_AA:c9d8be924ee7:a7d8c5d537e1'
        # assert res.sources_key() == 'c9d8be924ee7'
        # assert res.rlz == m.rlz TODO: need string coercion for sqladapter!
        # assert 0

    def test_HazardAggregation_table_save_get(self, adapted_model, generate_rev4_aggregation_models):

        m = next(generate_rev4_aggregation_models())
        print(m)
        mHAG = adapted_model.HazardAggregateCurve
        m.save()
        res = next(
            mHAG.query(
                m.partition_key,
                mHAG.sort_key == m.sort_key,
                # (mHRC.compatible_calc_fk == m.compatible_calc_fk)
                # & (mHRC.producer_config_fk == m.producer_config_fk)
                # & (mHRC.vs30 == m.vs30),  # filter_condition
            )
        )

        print(res)
        assert res.created.timestamp() == int(m.created.timestamp())  # approx
        assert res.vs30 == m.vs30
        assert res.imt == m.imt
        assert res.values[0] == m.values[0]
        assert res.sort_key == '-38.160~178.247:0250:PGA:mean:NSHM_DUMMY_MODEL'


@pytest.fixture
def pyarrow_aggregation_models(many_rlz_args):
    def generator_fn():
        for loc, vs30, imt, agg in itertools.product(
            many_rlz_args["locs"][:5], many_rlz_args["vs30s"], many_rlz_args["imts"], ['mean', 'cov', '0.95']
        ):
            yield HazardAggregateCurve(
                compatible_calc_id="NZSHM22",
                hazard_model_id="MyNewModel",
                nloc_001=loc.resample(0.001).code,
                nloc_0=loc.resample(1).code,
                imt=imt,
                vs30=vs30,
                aggr=agg,
                values=[(x / 1000) for x in range(44)],
            )

    yield generator_fn


# Test pyarrow HazardAggregation models
def test_HazardAggregation_roundtrip_dataset(pyarrow_aggregation_models, tmp_path):

    output_folder = tmp_path / "ds"

    models = pyarrow_aggregation_models()

    print(models)
    filesystem = fs.LocalFileSystem()

    # write the dataset
    pyarrow_aggr_dataset.append_models_to_dataset(models, output_folder, filesystem=filesystem)

    # read and check the dataset
    dataset = ds.dataset(output_folder, filesystem=filesystem, format='parquet', partitioning='hive')
    table = dataset.to_table()
    df = table.to_pandas()

    expected = pyarrow_aggr_dataset.table_from_models(pyarrow_aggregation_models())

    assert table.shape == expected.shape
    assert df.shape == expected.shape


def test_HazardAggregation_write_dataset_with_bad_schema(pyarrow_aggregation_models, tmp_path, monkeypatch):

    # monkeypatch with a bad schema
    bad_schema = pa.schema([("mumbo", pa.string()), ("jumbo", pa.string())])
    monkeypatch.setattr(pyarrow_aggr_dataset, "hazard_agreggate_schema", bad_schema)

    # should raise excption about the schema mismatch
    with pytest.raises(pa.ArrowTypeError, match=r"which does not match expected schema"):

        output_folder = tmp_path / "ds"
        models = pyarrow_aggregation_models()
        filesystem = fs.LocalFileSystem()

        pyarrow_aggr_dataset.append_models_to_dataset(models, output_folder, filesystem=filesystem)


def test_HazardAggregation_read_dataset_with_bad_schema_doesnt_fail(pyarrow_aggregation_models, tmp_path, monkeypatch):

    dataset_folder = tmp_path / "ds"
    models = pyarrow_aggregation_models()
    filesystem = fs.LocalFileSystem()

    pyarrow_aggr_dataset.append_models_to_dataset(models, dataset_folder, filesystem=filesystem)

    filesystem = fs.LocalFileSystem()
    dataset = ds.dataset(dataset_folder, schema=None, format='parquet', filesystem=filesystem, partitioning='hive')

    print()
    print(dataset.schema)
    print()

    # I epected this should raise exception about the schema mismatch
    # based on https://arrow.apache.org/docs/python/generated/pyarrow.\
    #  dataset.Dataset.html#pyarrow.dataset.Dataset.replace_schema
    bad_schema = pa.schema([("numeric", pa.int64()), ("mumbo", pa.string()), ("jumbo", pa.string())])
    dataset = dataset.replace_schema(bad_schema)  # should raise exception but doesn't

    table = dataset.to_table()
    df = table.to_pandas()
    print(df)  # still no exception
