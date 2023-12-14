# from moto import mock_dynamodb
# from nzshm_common.location.code_location import CodedLocation
import pytest
from pynamodb.attributes import UnicodeAttribute

from toshi_hazard_store.v2.db_adapter import ModelAdapterMixin, sqlite_adapter

MYADAPTER = sqlite_adapter.SqliteAdapter()


class MyAdapterTable(ModelAdapterMixin):
    class Meta:
        table_name = "MyFkAdapterTable"

    class AdapterMeta:
        adapter = MYADAPTER

    my_hash_key = UnicodeAttribute(hash_key=True)
    my_range_key = UnicodeAttribute(range_key=True)


@pytest.fixture(scope="module")
def sqlite_adapter_test_table():
    yield MyAdapterTable


def get_one_meta():
    return dict(hash_key="XYZ", range_key="AMCDEF:350")


def test_model_key_attribues(sqlite_adapter_test_table):
    from toshi_hazard_store.model.caching.cache_store import get_hash_key

    assert get_hash_key(sqlite_adapter_test_table) == 'my_hash_key'


def test_table_creation(sqlite_adapter_test_table):
    sqlite_adapter_test_table.create_table()
    assert sqlite_adapter_test_table.exists()


def test_table_create_drop(sqlite_adapter_test_table):
    sqlite_adapter_test_table.create_table()
    assert sqlite_adapter_test_table.exists()
    sqlite_adapter_test_table.delete_table()
    assert not sqlite_adapter_test_table.exists()


def test_table_save(sqlite_adapter_test_table):
    sqlite_adapter_test_table.create_table()
    obj = MyAdapterTable(my_hash_key="ABD123", my_range_key="qwerty123")
    obj.save()


def test_table_save_and_query(sqlite_adapter_test_table):
    sqlite_adapter_test_table.create_table()
    MyAdapterTable(my_hash_key="ABD123", my_range_key="qwerty123").save()
    res = sqlite_adapter_test_table.query(
        hash_key="ABD123", range_key_condition=MyAdapterTable.my_range_key == "qwerty123"
    )

    result = list(res)
    assert len(result) == 1
    assert isinstance(result[0], MyAdapterTable)
    assert result[0].my_hash_key == "ABD123"
    assert result[0].my_range_key == "qwerty123"


def test_table_save_and_query_many(sqlite_adapter_test_table):
    sqlite_adapter_test_table.delete_table()
    sqlite_adapter_test_table.create_table()
    assert sqlite_adapter_test_table.exists()

    for rk in range(10):
        MyAdapterTable(my_hash_key="ABD123", my_range_key=f"qwerty123-{rk}").save()

    res = sqlite_adapter_test_table.query(
        hash_key="ABD123",
    )

    result = list(res)
    assert len(result) == 10
    print(result)
    assert isinstance(result[0], MyAdapterTable)
    assert result[0].my_hash_key == "ABD123"
    assert result[0].my_range_key == "qwerty123-0"
    assert result[9].my_range_key == "qwerty123-9"