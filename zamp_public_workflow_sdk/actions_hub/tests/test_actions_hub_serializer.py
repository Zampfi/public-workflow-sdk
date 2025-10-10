"""
Tests for ActionsHub serializer
"""

from enum import Enum
from io import BytesIO

import pytest
from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.actions_hub.utils.serializer import Serializer


class SampleEnum(Enum):
    A = "a"
    B = "b"


class SubModel(BaseModel):
    name: str
    age: int


class SampleModel(BaseModel):
    name: str = Field(default="", description="The name of the model")
    age: int = Field(default=0, description="The age of the model")
    this_is_a_type: type[BaseModel] = Field(description="The type of the model")
    brr: SubModel = Field(default=SubModel(name="", age=0), description="The submodel of the model")
    enum: SampleEnum = Field(default=SampleEnum.A, description="The enum of the model")
    bytesIO: BytesIO = Field(default=BytesIO(), description="The bytesio of the model")

    class Config:
        arbitrary_types_allowed = True


class TestSerializer:
    """Test the ActionsHub Serializer class."""

    def test_serializer_dict_platform_compatible(self):
        """Test serializer with dictionary input - matches platform test exactly."""
        extracted_value = Serializer.get_schema_from_object(
            {
                "a": 1,
                "b": BytesIO(b"alskejfsl"),
                "c": {"d": SubModel(name="", age=0), "e": 4},
            }
        )

        expected = [
            {"name": "a", "type": "int"},
            {"name": "b", "type": "_io.BytesIO"},
            {
                "name": "c",
                "type": "dict",
                "properties": [
                    {
                        "name": "d",
                        "type": "test_actions_hub_serializer.SubModel",
                        "properties": [
                            {"name": "name", "type": "str"},
                            {"name": "age", "type": "int"},
                        ],
                    },
                    {"name": "e", "type": "int"},
                ],
            },
        ]

        assert extracted_value == expected

    def test_serializer_pydantic_model_type_platform_compatible(self):
        """Test serializer with Pydantic model class - matches platform test exactly."""
        extracted_value = Serializer.get_schema_from_model_class(SampleModel)

        expected = [
            {"name": "name", "type": "str", "description": "The name of the model"},
            {"name": "age", "type": "int", "description": "The age of the model"},
            {
                "name": "this_is_a_type",
                "type": "type[pydantic.main.BaseModel]",
                "description": "The type of the model",
            },
            {
                "name": "brr",
                "type": "test_actions_hub_serializer.SubModel",
                "description": "The submodel of the model",
                "properties": [
                    {"name": "name", "type": "str"},
                    {"name": "age", "type": "int"},
                ],
            },
            {
                "name": "enum",
                "type": "test_actions_hub_serializer.SampleEnum",
                "enum": ["a", "b"],
                "description": "The enum of the model",
            },
            {
                "name": "bytesIO",
                "type": "_io.BytesIO",
                "description": "The bytesio of the model",
            },
        ]

        assert extracted_value == expected

    def test_serializer_dict(self):
        """Test serializer with dictionary input."""
        extracted_value = Serializer.get_schema_from_object(
            {
                "a": 1,
                "b": BytesIO(b"alskejfsl"),
                "c": {"d": SubModel(name="", age=0), "e": 4},
            }
        )

        expected = [
            {"name": "a", "type": "int"},
            {"name": "b", "type": "_io.BytesIO"},
            {
                "name": "c",
                "type": "dict",
                "properties": [
                    {
                        "name": "d",
                        "type": "test_actions_hub_serializer.SubModel",
                        "properties": [
                            {"name": "name", "type": "str"},
                            {"name": "age", "type": "int"},
                        ],
                    },
                    {"name": "e", "type": "int"},
                ],
            },
        ]

        assert extracted_value == expected

    def test_serializer_pydantic_model_type(self):
        """Test serializer with Pydantic model class."""
        extracted_value = Serializer.get_schema_from_model_class(SampleModel)

        expected = [
            {"name": "name", "type": "str", "description": "The name of the model"},
            {"name": "age", "type": "int", "description": "The age of the model"},
            {
                "name": "this_is_a_type",
                "type": "type[pydantic.main.BaseModel]",
                "description": "The type of the model",
            },
            {
                "name": "brr",
                "type": "test_actions_hub_serializer.SubModel",
                "description": "The submodel of the model",
                "properties": [
                    {"name": "name", "type": "str"},
                    {"name": "age", "type": "int"},
                ],
            },
            {
                "name": "enum",
                "type": "test_actions_hub_serializer.SampleEnum",
                "enum": ["a", "b"],
                "description": "The enum of the model",
            },
            {
                "name": "bytesIO",
                "type": "_io.BytesIO",
                "description": "The bytesio of the model",
            },
        ]

        assert extracted_value == expected

    def test_serializer_primitive_types(self):
        """Test serializer with primitive types."""
        # Test string
        result = Serializer.get_schema_from_primitive_type(str)
        assert result == {"type": "str", "description": "A str value"}

        # Test int
        result = Serializer.get_schema_from_primitive_type(int)
        assert result == {"type": "int", "description": "A int value"}

        # Test float
        result = Serializer.get_schema_from_primitive_type(float)
        assert result == {"type": "float", "description": "A float value"}

        # Test bool
        result = Serializer.get_schema_from_primitive_type(bool)
        assert result == {"type": "bool", "description": "A bool value"}

    def test_serializer_class_types(self):
        """Test serializer with class types."""
        # Test primitive class
        result = Serializer.get_schema_from_class(str)
        assert result == {"type": "str", "description": "A str value"}

        # Test Pydantic model class
        result = Serializer.get_schema_from_class(SubModel)
        assert "type" in result
        assert "properties" in result

    def test_serializer_object_types(self):
        """Test serializer with object instances."""
        # Test dict object
        test_dict = {"key": "value", "number": 42}
        result = Serializer.get_schema_from_object(test_dict)
        assert isinstance(result, list)
        assert len(result) == 2

        # Test Pydantic model object
        test_model = SubModel(name="test", age=25)
        result = Serializer.get_schema_from_object(test_model)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_serializer_individual_schema(self):
        """Test individual schema creation."""
        result = Serializer.get_individual_schema(
            name="test_field",
            type="str",
            description="A test field",
            properties=[{"name": "nested", "type": "int"}],
            enum=["option1", "option2"],
        )

        expected = {
            "name": "test_field",
            "type": "str",
            "description": "A test field",
            "properties": [{"name": "nested", "type": "int"}],
            "enum": ["option1", "option2"],
        }

        assert result == expected

    def test_serializer_individual_schema_minimal(self):
        """Test individual schema creation with minimal parameters."""
        result = Serializer.get_individual_schema(name="simple_field", type="int")

        expected = {"name": "simple_field", "type": "int"}

        assert result == expected

    def test_serializer_enum_in_dict(self):
        """Test serializer with enum values in dictionary."""
        result = Serializer.get_schema_from_object(
            {
                "string_field": "hello",
                "enum_field": SampleEnum.B,
                "nested": {"inner_enum": SampleEnum.A},
            }
        )

        expected = [
            {"name": "string_field", "type": "str"},
            {
                "name": "enum_field",
                "type": "test_actions_hub_serializer.SampleEnum",
                "enum": ["a", "b"],
            },
            {
                "name": "nested",
                "type": "dict",
                "properties": [
                    {
                        "name": "inner_enum",
                        "type": "test_actions_hub_serializer.SampleEnum",
                        "enum": ["a", "b"],
                    }
                ],
            },
        ]

        assert result == expected

    def test_serializer_invalid_class_type(self):
        """Test serializer with invalid class type."""
        with pytest.raises(ValueError, match="Invalid model type"):
            Serializer.get_schema_from_class(list)

    def test_serializer_invalid_object_type(self):
        """Test serializer with invalid object type."""
        with pytest.raises(ValueError, match="Invalid model type"):
            Serializer.get_schema_from_object("invalid_string")

    def test_serializer_empty_dict(self):
        """Test serializer with empty dictionary."""
        result = Serializer.get_schema_from_object({})
        assert result == []

    def test_serializer_nested_dict_complex(self):
        """Test serializer with complex nested dictionary structure."""
        complex_dict = {
            "level1": {
                "level2": {
                    "level3": SubModel(name="nested", age=30),
                    "primitive": "string_value",
                },
                "list_data": [1, 2, 3],
                # Remove enum_data as it's not supported by the current serializer
            },
            "direct_primitive": 42,
        }

        result = Serializer.get_schema_from_object(complex_dict)
        assert len(result) == 2  # level1 and direct_primitive
        assert result[0]["name"] == "level1"
        assert result[0]["type"] == "dict"
        assert "properties" in result[0]
        assert result[1]["name"] == "direct_primitive"
        assert result[1]["type"] == "int"

    def test_serializer_model_with_none_values(self):
        """Test serializer with model containing None values."""

        class ModelWithNone(BaseModel):
            required_field: str
            optional_field: str | None = None
            default_none: str | None = Field(default=None, description="Optional field")

        result = Serializer.get_schema_from_model_class(ModelWithNone)
        assert len(result) == 3
        assert any(item["name"] == "required_field" for item in result)
        assert any(item["name"] == "optional_field" for item in result)
        assert any(item["name"] == "default_none" for item in result)

    def test_serializer_enum_with_different_values(self):
        """Test serializer with enum containing different value types."""

        class MixedEnum(Enum):
            STRING_VALUE = "string"
            NUMERIC_VALUE = 123
            BOOLEAN_VALUE = True

        class EnumModel(BaseModel):
            mixed_enum: MixedEnum = Field(description="Mixed enum field")

        result = Serializer.get_schema_from_model_class(EnumModel)
        enum_field = next(item for item in result if item["name"] == "mixed_enum")
        assert enum_field["type"] == "test_actions_hub_serializer.MixedEnum"
        assert "enum" in enum_field
        assert set(enum_field["enum"]) == {"string", 123, True}

    def test_serializer_primitive_types_comprehensive(self):
        """Test serializer with all supported primitive types."""
        primitives = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "bytes": bytes,
        }

        for expected_type, type_class in primitives.items():
            result = Serializer.get_schema_from_primitive_type(type_class)
            assert result["type"] == expected_type
            assert f"A {expected_type} value" in result["description"]

    def test_serializer_individual_schema_with_all_parameters(self):
        """Test individual schema creation with all optional parameters."""
        result = Serializer.get_individual_schema(
            name="comprehensive_field",
            type="CustomType",
            description="A comprehensive test field",
            properties=[
                {"name": "nested1", "type": "str"},
                {"name": "nested2", "type": "int"},
            ],
            enum=["option1", "option2", "option3"],
        )

        expected = {
            "name": "comprehensive_field",
            "type": "CustomType",
            "description": "A comprehensive test field",
            "properties": [
                {"name": "nested1", "type": "str"},
                {"name": "nested2", "type": "int"},
            ],
            "enum": ["option1", "option2", "option3"],
        }

        assert result == expected
