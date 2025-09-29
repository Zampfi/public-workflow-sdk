import pytest
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
    assert payload is not None
    assert "encoding" in payload.metadata
    dict["bytes_io"] = BytesIO(b"test")

    converter.from_payload(payload, Dict[str, Any])

    payload = converter.to_payload(dict)
    assert DEFAULT_CONVERTER_METADATA_KEY not in payload.metadata

@pytest.mark.xfail(reason="Pydantic cannot serialize ModelMetaclass types")
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
    assert payload is not None
    assert "encoding" in payload.metadata
    converter.from_payload(payload, Basic)
    payload = converter.to_payload(nested1)
    assert payload is not None
    assert "encoding" in payload.metadata
    converter.from_payload(payload, Nested1)
    payload = converter.to_payload(nested2)
    assert payload is not None
    assert "encoding" in payload.metadata
    converter.from_payload(payload, Nested2)

def test_generic_case():
    from pydantic import BaseModel, Field
    from typing import Any, Dict, Optional
    from typing import TypeVar

    T = TypeVar("T", bound=BaseModel)

    class ExecutionResult[T: BaseModel](BaseModel):
        success: bool = Field(..., description="Whether the execution was successful")
        result: Optional[T] = Field(
            None, description="Result of the function execution if successful"
        )
        error: Optional[str] = Field(None, description="Error message if execution failed")
        execution_time: float = Field(
            ..., description="Time taken for execution in seconds"
        )

    converter = PydanticJSONPayloadConverter()
    execution_result = ExecutionResult(
        success=True,
        result=Basic(string="test"),
        error=None,
        execution_time=1.0
    )
    payload = converter.to_payload(execution_result)
    assert DEFAULT_CONVERTER_METADATA_KEY not in payload.metadata

if __name__ == "__main__":
    test_basic()
    test_nested_case()
    test_generic_case()