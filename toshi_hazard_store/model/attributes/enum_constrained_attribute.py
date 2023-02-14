"""This module defines some custom enum attributes."""

from enum import Enum
from typing import Any, Type, TypeVar, Union

from pynamodb.attributes import Attribute
from pynamodb.constants import NUMBER, STRING

T = TypeVar("T", bound=Enum)


class EnumConstrainedAttribute(Attribute[T]):
    """
    Stores strings or numbers that are values of the supplied Enum as DynamoDB strings.

    Useful where you have values in an existing table field and you want retrofit Enum validation.

    Otherwise, consider using the EnumAttribute class below and

    >>> from enum import Enum
    >>> from pynamodb.models import Model
    >>>
    >>> class ShakeFlavor(Enum):
    >>>   VANILLA = 'vanilla'
    >>>   MINT = 'mint'
    >>>
    >>> class Shake(Model):
    >>>   flavor = EnumConstrainedAttribute(ShakeFlavor)
    >>>
    >>> modelB = Shake(flavor='mint')
    >>>
    """

    def __init__(self, enum_type: Type[T], attr_type: str = STRING, **kwargs: Any) -> None:
        """
        :param enum_type: The type of the enum
        """
        assert attr_type in [STRING, NUMBER]
        self.attr_type = attr_type

        super().__init__(**kwargs)
        self.enum_type = enum_type

        self.valid_types = (str,) if attr_type == STRING else (int, float)
        if not all(isinstance(e.value, self.valid_types) for e in self.enum_type):
            raise TypeError(
                f"Enumeration '{self.enum_type}' values must be all {self.valid_types}",
            )

    def deserialize(self, value: Union[str, float, int]) -> Union[str, float, int]:
        try:
            assert self.enum_type(value)
            return value
        except (ValueError):
            raise ValueError(f'value {value} must be a member of {self.enum_type}')

    def serialize(self, value: Union[str, float, int]) -> Union[str, float, int]:
        try:
            if not isinstance(value, self.valid_types):
                raise ValueError(f'value {value} must be a member of {self.enum_type}')
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


class NumberEnumAttribute(Attribute[T]):
    """
    Stores names of the supplied Enum as DynamoDB number.

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

    attr_type = NUMBER

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
