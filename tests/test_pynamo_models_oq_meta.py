from moto import mock_dynamodb

from toshi_hazard_store.model import openquake_models


@mock_dynamodb
class TestToshiOpenquakeMetaModel:
    def test_table_exists(self):
        # assert adapted_model.OpenquakeRealization.exists()
        assert not openquake_models.ToshiOpenquakeMeta.exists()
        openquake_models.ToshiOpenquakeMeta.create_table(wait=True)
        assert openquake_models.ToshiOpenquakeMeta.exists()

    def test_save_one_meta_object(self, get_one_meta):
        print(openquake_models.__dict__['ToshiOpenquakeMeta'].__bases__)
        openquake_models.ToshiOpenquakeMeta.create_table(wait=True)
        obj = get_one_meta(openquake_models.ToshiOpenquakeMeta)
        obj.save()
        assert obj.inv_time == 1.0
