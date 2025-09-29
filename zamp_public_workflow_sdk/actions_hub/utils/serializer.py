"""
Serializer for ActionsHub - independent of Pantheon platform.
"""

from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from typing import Dict, Any

from .utils import get_fqn


class Serializer:
    @classmethod
    def get_schema_from_model_class(cls, model: type[BaseModel]):
        """
        Get schema from a Pydantic model class by iterating through its fields.

        Args:
            model: The Pydantic model class to get schema for

        Returns:
            List of dictionaries containing the schema information for each field
        """
        result = []
        for name, field in model.model_fields.items():
            if (
                field.annotation is not None
                and isinstance(field.annotation, type)
                and issubclass(field.annotation, Enum)
            ):
                result.append(
                    cls.get_individual_schema(
                        name,
                        get_fqn(field.annotation),
                        field.description,
                        enum=[e.value for e in field.annotation],
                    )
                )
                continue

            if (
                field.annotation is not None
                and isinstance(field.annotation, type)
                and issubclass(field.annotation, BaseModel)
            ):
                result.append(
                    cls.get_individual_schema(
                        name,
                        get_fqn(field.annotation),
                        field.description,
                        properties=cls.get_schema_from_model_class(field.annotation),
                    )
                )
                continue

            result.append(
                cls.get_individual_schema(
                    name,
                    get_fqn(field.annotation)
                    if field.annotation is not None
                    else "None",
                    field.description,
                )
            )

        return result

    @classmethod
    def get_schema_from_class(cls, model: type[Any]):
        """
        Get schema from a class type.

        Args:
            model: The class type to get schema for

        Returns:
            Dictionary containing the schema information
        """
        if model in (str, int, float, bool, bytes, datetime):
            return cls.get_schema_from_primitive_type(model)
        elif isinstance(model, type) and issubclass(model, BaseModel):
            return model.model_json_schema()
        else:
            raise ValueError("Invalid model type")

    @classmethod
    def get_schema_from_object(cls, model: Any):
        """
        Get schema from an object instance.

        Args:
            model: The object to get schema for

        Returns:
            Schema information for the object
        """
        if isinstance(model, dict):
            return cls.get_schema_from_dict(model)
        elif isinstance(model, BaseModel):
            return cls.get_schema_from_model_class(type(model))
        elif isinstance(model, Enum):
            # Handle enum instances by returning their enum values
            return [e.value for e in type(model)]
        else:
            raise ValueError("Invalid model type")

    @classmethod
    def get_schema_from_primitive_type(cls, model: Any):
        """
        Get schema for primitive types.

        Args:
            model: The primitive type

        Returns:
            Dictionary containing the schema information
        """
        type_name = model.__name__ if isinstance(model, type) else type(model).__name__
        return {"type": type_name, "description": f"A {type_name} value"}

    @classmethod
    def get_schema_from_dict(cls, model: Dict[str, Any]):
        """
        Get schema from a dictionary.

        Args:
            model: The dictionary to get schema for

        Returns:
            List of dictionaries containing the schema information
        """
        result = []
        for key, value in model.items():
            try:
                inner_schema = cls.get_schema_from_object(value)
                # Check if the inner schema is enum values (list) or properties (dict/list of dicts)
                if isinstance(inner_schema, list) and isinstance(value, Enum):
                    # Handle enum case
                    current_result = cls.get_individual_schema(
                        key, get_fqn(type(value)), enum=inner_schema
                    )
                else:
                    # Handle other cases (BaseModel, dict, etc.)
                    current_result = cls.get_individual_schema(
                        key, get_fqn(type(value)), properties=inner_schema
                    )
            except ValueError:
                # Fallback for unsupported types
                current_result = cls.get_individual_schema(key, get_fqn(type(value)))

            result.append(current_result)

        return result

    @classmethod
    def get_individual_schema(
        cls, name, type, description="", properties=None, enum=None
    ):
        """
        Create an individual schema entry.

        Args:
            name: The field name
            type: The field type
            description: The field description
            properties: Nested properties (for complex types)
            enum: Enum values (for enum types)

        Returns:
            Dictionary containing the schema entry
        """
        result = {"name": name, "type": type}

        if description:
            result["description"] = description
        if properties:
            result["properties"] = properties
        if enum:
            result["enum"] = enum

        return result
