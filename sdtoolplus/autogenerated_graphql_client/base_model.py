# Generated by ariadne-codegen on 2025-02-06 10:31
from typing import Any
from typing import Dict
from typing import get_args
from typing import get_origin
from typing import Type
from typing import Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic.class_validators import validator
from pydantic.fields import ModelField

from .scalars import SCALARS_PARSE_FUNCTIONS
from .scalars import SCALARS_SERIALIZE_FUNCTIONS


class UnsetType:
    def __bool__(self) -> bool:
        return False


UNSET = UnsetType()


class BaseModel(PydanticBaseModel):
    class Config:
        allow_population_by_field_name = True
        validate_assignment = True
        arbitrary_types_allowed = True

    # pylint: disable=no-self-argument
    @validator("*", pre=True)
    def parse_custom_scalars(cls, value: Any, field: ModelField) -> Any:
        return cls._parse_custom_scalar_value(value, field.annotation)

    @classmethod
    def _parse_custom_scalar_value(cls, value: Any, type_: Type[Any]) -> Any:
        origin = get_origin(type_)
        args = get_args(type_)
        if origin is list and isinstance(value, list):
            return [cls._parse_custom_scalar_value(item, args[0]) for item in value]

        if origin is Union and type(None) in args:
            sub_type: Any = list(filter(None, args))[0]
            return cls._parse_custom_scalar_value(value, sub_type)

        decode = SCALARS_PARSE_FUNCTIONS.get(type_)
        if value and decode and callable(decode):
            return decode(value)

        return value

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        dict_ = super().dict(**kwargs)
        return {key: self._serialize_value(value) for key, value in dict_.items()}

    def _serialize_value(self, value: Any) -> Any:
        serialize = SCALARS_SERIALIZE_FUNCTIONS.get(type(value))
        if serialize and callable(serialize):
            return serialize(value)

        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]

        return value
