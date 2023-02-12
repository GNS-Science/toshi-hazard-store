"""This module defines some custom attributes."""

from enum import Enum
from typing import Any, Type, TypeVar

from pynamodb.attributes import Attribute
from pynamodb.constants import STRING

T = TypeVar("T", bound=Enum)


class UnicodeEnumConstrainedAttribute(Attribute[T]):
    """
    Stores strings that are values of the supplied Enum as DynamoDB strings.

    Useful where you have value strings in an existing table field and you want retrofit the Enum validation.

    Otherwise, consider using the EnumAttribute class below and expect

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


class EnumAttribute(Attribute[T]):
    """
    Stores names of the supplied Enum as DynamoDB strings.

    >>> from enum import Enum
    >>>
    >>> from pynamodb.models import Model
    >>>
    >>> class ShakeFlavor(Enum):
    >>>   VANILLA = 0.1
    >>>   MINT = 1.22
    >>>
    >>> class Shake(Model):
    >>>   flavor = EnumAttribute(ShakeFlavor)
    >>>
    >>> modelB = Shake(flavor=ShakeFlavor.MINT)
    >>> assert modelB.flavor == ShakeFlavor.MINT
    """

    attr_type = STRING

    def __init__(self, enum_type: Type[T], **kwargs: Any) -> None:
        """
        :param enum_type: The type of the enum
        """
        super().__init__(**kwargs)
        self.enum_type = enum_type

    def deserialize(self, name: str) -> Type[T]:
        try:
            return getattr(self.enum_type, name)
            return name
        except (AttributeError):
            raise ValueError(f'stored value {name} must be a value of  {self.enum_type}.')

    def serialize(self, instance: Type[T]) -> str:
        if isinstance(instance, self.enum_type):
            return instance.name
        raise ValueError(f'value {instance} must be a {self.enum_type} or an instance.')
