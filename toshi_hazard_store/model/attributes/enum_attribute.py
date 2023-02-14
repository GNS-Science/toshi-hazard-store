"""This module defines a custom enum attribute."""
from enum import Enum
from typing import Any, Type, TypeVar

from pynamodb.attributes import Attribute
from pynamodb.constants import STRING

T = TypeVar("T", bound=Enum)


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
