"""This module defines some custom attributes."""


import json
from typing import Any, Dict, List, Union

from nzshm_common.util import compress_string, decompress_string
from pynamodb.attributes import Attribute, ListAttribute, MapAttribute, NumberAttribute, UnicodeAttribute
from pynamodb.constants import STRING


class IMTValuesAttribute(MapAttribute):
    """Store the IntensityMeasureType e.g.(PGA, SA(N)) and the levels and values lists."""

    imt = UnicodeAttribute()
    lvls = ListAttribute(of=NumberAttribute)
    vals = ListAttribute(of=NumberAttribute)


class LevelValuePairAttribute(MapAttribute):
    """Store the IMT level and the POE value at the level."""

    lvl = NumberAttribute(null=False)
    val = NumberAttribute(null=False)


class CompressedJsonicAttribute(Attribute):
    """
    A compressed, json serialisable model attribute
    """

    attr_type = STRING

    def serialize(self, value: Any) -> str:
        return compress_string(json.dumps(value))  # could this be pickle??

    def deserialize(self, value: str) -> Union[Dict, List]:
        return json.loads(decompress_string(value))


class CompressedListAttribute(CompressedJsonicAttribute):
    """
    A compressed list of floats attribute.
    """

    def serialize(self, value: List[float]) -> str:
        if value is not None and not isinstance(value, list):
            raise TypeError(
                f"value has invalid type '{type(value)}'; List[float])expected",
            )
        return super().serialize(value)
