"""This module defines some custom attributes."""

from enum import Enum
from typing import Any, Type, TypeVar

from pynamodb.attributes import Attribute
from pynamodb.constants import STRING

T = TypeVar("T", bound=Enum)


class UnicodeEnumConstrainedAttribute(Attribute[T]):
    """
    Stores strings that are values of the supplied Enum as DynamoDB strings.

    >>> from enum import Enum
    >>>
    >>> from pynamodb.models import Model
    >>>
    >>> class ShakeFlavor(Enum):
    >>>   VANILLA = 'vanilla'
    >>>   CHOCOLATE = 'chocolate'
    >>>   COOKIES = 'cookies'
    >>>   MINT = 'mint'
    >>>
    >>> class Shake(Model):
    >>>   flavor = UnicodeEnumConstrainedAttribute(ShakeFlavor)
    >>>
    >>> modelB = Shake(flavor='mint')
    >>>
    """

    attr_type = STRING

    def __init__(self, enum_type: Type[T], **kwargs: Any) -> None:
        """
        :param enum_type: The type of the enum
        """
        super().__init__(**kwargs)
        self.enum_type = enum_type
        if not all(isinstance(e.value, str) for e in self.enum_type):
            raise TypeError(
                f"Enumeration '{self.enum_type}' values must be all strings",
            )

    def deserialize(self, value: str) -> str:
        try:
            assert self.enum_type(value)
            return value
        except (ValueError) as err:
            raise err

    def serialize(self, value: str) -> str:
        try:
            if not isinstance(value, str):
                raise ValueError(f'value {value} must be a string value from {self.enum_type}')
            self.enum_type(value)
        except (ValueError) as err:
            raise err
        return value