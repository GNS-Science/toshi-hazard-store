import os
import pytest
import numpy as np
from pathlib import Path
from toshi_hazard_store.model.attributes import UnicodeEnumConstrainedAttribute
from toshi_hazard_store.model import AggregationEnum


INVALID_ARGS_LIST = [AggregationEnum.MEAN, object(), 'MEAN', {}]

folder = Path(Path(os.path.realpath(__file__)).parent, 'fixtures', 'disaggregation')
disaggs = np.load(Path(folder, 'deagg_SLT_v8_gmm_v2_FINAL_-39.000~175.930_750_SA(0.5)_86_eps-dist-mag-trt.npy'))


class TestUnicodeEnumConstrainedAttribute(object):
    def test_serialize_a_valid_str(self):
        assert AggregationEnum('mean') == AggregationEnum.MEAN
        attr = UnicodeEnumConstrainedAttribute(AggregationEnum)
        assert attr.serialize('mean') == AggregationEnum.MEAN.value

    def test_deserialize_a_valid_str(self):
        assert AggregationEnum('mean') == AggregationEnum.MEAN
        attr = UnicodeEnumConstrainedAttribute(AggregationEnum)
        assert attr.deserialize('mean') == AggregationEnum.MEAN.value

    def test_serialize_an_unknown_str_raises_value_err(self):
        attr = UnicodeEnumConstrainedAttribute(AggregationEnum)
        val = 'NAHH'
        with pytest.raises(ValueError) as ctx:
            attr.serialize(val)

        # print(ctx.exception)
        print(dir(ctx))
        assert val in repr(ctx.value)

    def test_deserialize_an_unknown_str_raises_value_err(self):
        attr = UnicodeEnumConstrainedAttribute(AggregationEnum)
        val = 'NAHH'
        with pytest.raises(ValueError) as ctx:
            attr.deserialize(val)

        # print(ctx.exception)
        print(dir(ctx))
        assert val in repr(ctx.value)

    @pytest.mark.parametrize('invalid_arg', [AggregationEnum.MEAN, object(), 'MEAN', {}])
    def test_serialize_an_unknown_type_raises_value_err(self, invalid_arg):
        attr = UnicodeEnumConstrainedAttribute(AggregationEnum)

        with pytest.raises(ValueError) as ctx:
            attr.serialize(invalid_arg)
        assert 'AggregationEnum' in repr(ctx.value)

    def test_attribute_compression(self):
        """Test if compressing the numpy adday is worthwhile."""
        print("Size of the array: ", disaggs.size)
        print("Memory size of one array element in bytes: ", disaggs.itemsize)
        array_size = disaggs.size * disaggs.itemsize
        print("Memory size of numpy array in bytes:", array_size)

        import zlib
        import sys
        import pickle

        comp = zlib.compress(pickle.dumps(disaggs))
        uncomp = pickle.loads(zlib.decompress(comp))

        assert uncomp.all() == disaggs.all()
        assert sys.getsizeof(comp) < array_size / 5
