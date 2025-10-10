from pydantic import BaseModel
from datetime import datetime
from io import BytesIO
from typing import Any


class TestModelWithInteger(BaseModel):
    integer: int


class TestModelWithString(BaseModel):
    string: str


class TestModelWithListOfIntegers(BaseModel):
    integers: list[int]


class TestModelWithPydanticType(BaseModel):
    pydantic_type: type[BaseModel]


class TestModelCompositeModel(BaseModel):
    integer: TestModelWithInteger
    string: TestModelWithString
    integers: list[TestModelWithInteger]
    bytesIo: BytesIO
    bytes: bytes
    datetime: datetime
    type_obj: type[BaseModel]

    class Config:
        arbitrary_types_allowed = True


class TestModelWithGenericTypeVar[T: BaseModel](BaseModel):
    generic_type_var: T
    list_generic_type_var: list[T]


class TestModelWithGenericDictionary(BaseModel):
    generic_dict: dict[str, Any]


class TestModelWithUnion(BaseModel):
    union: int | str
    optional: int | None = None


class TestModelWithTuple(BaseModel):
    tuple: tuple


class TestModelWithUnionAndOptional[T: BaseModel](BaseModel):
    data: dict[str, Any] | T | None


class TestModelWithAny(BaseModel):
    any: Any


class TestModelWithOptionalAny(BaseModel):
    optional_any: Any | None = None
