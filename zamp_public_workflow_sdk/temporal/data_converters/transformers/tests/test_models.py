from pydantic import BaseModel
from datetime import datetime
from io import BytesIO
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_transformer import PydanticTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_var_transformer import PydanticTypeVarTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.list_transformer import ListTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytes_transformer import BytesTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytesio_transformer import BytesIOTransformer
from typing import Any, Dict, Type

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