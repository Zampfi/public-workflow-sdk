from __future__ import annotations

from io import BytesIO
from typing import Any, Dict

from pydantic import BaseModel

from zamp_public_workflow_sdk.temporal.data_converters.pydantic_payload_converter import (
    DEFAULT_CONVERTER_METADATA_KEY,
    PydanticJSONPayloadConverter,
)


class Basic(BaseModel):
    string: str


class Nested1(BaseModel):
    basic: Basic


class Nested2(BaseModel):
    nested1: Nested1
    type_var: type[BaseModel]


def test_basic():
    converter = PydanticJSONPayloadConverter()
    dict = {"string": "test", "integer": 1}

    payload = converter.to_payload(dict)
    assert DEFAULT_CONVERTER_METADATA_KEY in payload.metadata
    dict["bytes_io"] = BytesIO(b"test")

    converter.from_payload(payload, dict[str, Any])

    payload = converter.to_payload(dict)
    assert DEFAULT_CONVERTER_METADATA_KEY not in payload.metadata


def test_nested_case():
    converter = PydanticJSONPayloadConverter()

    basic1 = Basic(string="test")

    nested1 = Nested1(basic=basic1)

    nested2 = Nested2(nested1=nested1, type_var=Basic)

    payload = converter.to_payload(basic1)
    assert DEFAULT_CONVERTER_METADATA_KEY in payload.metadata
    converter.from_payload(payload, Basic)
    payload = converter.to_payload(nested1)
    assert DEFAULT_CONVERTER_METADATA_KEY in payload.metadata
    converter.from_payload(payload, Nested1)
    payload = converter.to_payload(nested2)
    assert DEFAULT_CONVERTER_METADATA_KEY not in payload.metadata
    converter.from_payload(payload, Nested2)


def test_generic_case():
    from typing import Generic, Optional, TypeVar

    from pydantic import BaseModel, Field

    T = TypeVar("T", bound=BaseModel)

    class ExecutionResult(BaseModel, Generic[T]):
        success: bool = Field(..., description="Whether the execution was successful")
        result: T | None = Field(None, description="Result of the function execution if successful")
        error: str | None = Field(None, description="Error message if execution failed")
        execution_time: float = Field(..., description="Time taken for execution in seconds")

    converter = PydanticJSONPayloadConverter()
    execution_result = ExecutionResult(success=True, result=Basic(string="test"), error=None, execution_time=1.0)
    payload = converter.to_payload(execution_result)
    assert DEFAULT_CONVERTER_METADATA_KEY not in payload.metadata


if __name__ == "__main__":
    test_basic()
    test_nested_case()
    test_generic_case()
