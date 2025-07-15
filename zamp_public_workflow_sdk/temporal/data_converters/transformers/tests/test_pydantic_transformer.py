from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models import TestModelWithInteger, TestModelWithListOfIntegers, TestModelCompositeModel, TestModelWithString, TestModelWithGenericTypeVar, TestModelWithGenericDictionary, TestModelWithPydanticType, TestModelWithUnion, TestModelWithTuple, TestModelWithUnionAndOptional, TestModelWithAny, TestModelWithOptionalAny
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn
from zamp_public_workflow_sdk.temporal.data_converters.pydantic_payload_converter import PydanticJSONPayloadConverter, DEFAULT_CONVERTER_METADATA_KEY
from io import BytesIO
from pydantic import BaseModel
from typing import Any, Dict

class Basic(BaseModel):
        string: str

class Nested1(BaseModel):
    basic: Basic

class Nested2(BaseModel):
    nested1: Nested1
    type_var: type[BaseModel]

def test_basic():
    converter = PydanticJSONPayloadConverter()
    dict = {
        "string": "test",
        "integer": 1
    }

    payload = converter.to_payload(dict)
    assert DEFAULT_CONVERTER_METADATA_KEY in payload.metadata
    dict["bytes_io"] = BytesIO(b"test")

    converter.from_payload(payload, Dict[str, Any])

    payload = converter.to_payload(dict)
    assert DEFAULT_CONVERTER_METADATA_KEY not in payload.metadata

def test_nested_case():
    converter = PydanticJSONPayloadConverter()

    basic1 = Basic(
        string="test"
    )

    nested1 = Nested1(
        basic=basic1
    )

    nested2 = Nested2(
        nested1=nested1,
        type_var=Basic
    )

    payload = converter.to_payload(basic1)
    assert DEFAULT_CONVERTER_METADATA_KEY in payload.metadata
    converter.from_payload(payload, Basic)
    payload = converter.to_payload(nested1)
    assert DEFAULT_CONVERTER_METADATA_KEY in payload.metadata
    converter.from_payload(payload, Nested1)
    payload = converter.to_payload(nested2)
    assert DEFAULT_CONVERTER_METADATA_KEY not in payload.metadata
    converter.from_payload(payload, Nested2)

if __name__ == "__main__":
    test_basic()
    test_nested_case()