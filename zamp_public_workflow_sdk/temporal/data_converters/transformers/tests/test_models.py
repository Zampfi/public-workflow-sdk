from pydantic import BaseModel
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Type, Optional, Union

class TestModelWithInteger(BaseModel):
    integer: int

class TestModelWithString(BaseModel):
    string: str

class TestModelWithListOfIntegers(BaseModel):
    integers: list[int]

class TestModelWithPydanticType(BaseModel):
    pydantic_type: Type[BaseModel]

class TestModelCompositeModel(BaseModel):
    integer: TestModelWithInteger
    string: TestModelWithString
    integers: list[TestModelWithInteger]
    bytesIo: BytesIO
    bytes: bytes
    datetime: datetime

    class Config:
        arbitrary_types_allowed = True

class TestModelWithGenericTypeVar[T: BaseModel](BaseModel):
    generic_type_var: T
    list_generic_type_var: list[T]

class TestModelWithGenericDictionary(BaseModel):
    generic_dict: Dict[str, Any]

class TestModelWithUnion(BaseModel):
    union: Union[int, str]
    optional: Optional[int] = None

class TestModelWithTuple(BaseModel):
    tuple: tuple

class TestModelWithUnionAndOptional[T: BaseModel](BaseModel):
    data: Optional[Union[Dict[str, Any], T]]

class TestModelWithAny(BaseModel):
    any: Any

class TestModelWithOptionalAny(BaseModel):
    optional_any: Optional[Any] = None
