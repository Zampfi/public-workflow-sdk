from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from typing import Any, Dict
from pydantic import BaseModel
from pydantic_core import to_jsonable_python
from pydantic.fields import FieldInfo
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_type_field_name, get_fqn, safe_issubclass, is_dict_type, is_pydantic_model, get_reference_from_fqn

class Transformer:
    _transformers: list[BaseTransformer] = []

    @classmethod
    def register_transformer(cls, transformer: BaseTransformer):
        cls._transformers.append(transformer)

    @classmethod
    def serialize(cls, value, type_hint: Any=None) -> Any:
        return cls._serialize(value, type_hint).serialized_value

    @classmethod
    def _serialize(cls, value, type_hint: Any=None) -> GenericSerializedValue:
        # Temporary hack to serialize ColumnMappingResult
        if "TableDetectionOutput" in str(type(value)):
            return to_jsonable_python(value)
        
        if value is None:
            return GenericSerializedValue(
                serialized_value=value,
                serialized_type_hint=get_fqn(type_hint)
            )
    
        for transformer in cls._transformers:
            serialized = transformer.serialize(value, type_hint)
            if serialized is not None:
                return serialized
        
        if cls._should_serialize(value, type_hint):
            serialized_result = {}
            for item_key, item_type, item_value in cls._get_enumerator(value):
                serialized = cls._serialize(item_value, item_type)
                if type(serialized) is GenericSerializedValue:
                    serialized_result[item_key] = serialized.serialized_value
                    serialized_result[get_type_field_name(item_key)] = serialized.serialized_type_hint
                else:
                    serialized_result[item_key] = serialized
                
            return GenericSerializedValue(
                serialized_value=serialized_result,
                serialized_type_hint=get_fqn(type_hint)
            )
            
        return GenericSerializedValue(
            serialized_value=to_jsonable_python(value),
            serialized_type_hint=get_fqn(type_hint)
        )

    @classmethod
    def deserialize(cls, value: Any, type_hint: Any) -> Any:
        if type_hint is None or value is None:
            return value
        
        if cls._should_deserialize(type_hint):
            if isinstance(value, GenericSerializedValue):
                type_hint = get_reference_from_fqn(value.serialized_type_hint)
                value = value.serialized_value

            deserialized_result = cls._default_deserialized_model(value, type_hint)
            for item_key, item_type, item_value in cls._get_enumerator(deserialized_result):
                if item_key.startswith("__") and item_key.endswith("_type"):
                    continue

                type_key = get_type_field_name(item_key)
                if type_key in value:
                    item_value = GenericSerializedValue(
                        serialized_value=cls._get_attribute(value, item_key),
                        serialized_type_hint=cls._get_attribute(value, type_key)
                    )

                deserialized = cls.deserialize(item_value, item_type)
                cls._set_attribute(deserialized_result, item_key, deserialized)

            return deserialized_result
                
        for transformer in cls._transformers:
            deserialized = transformer.deserialize(value, type_hint)
            if deserialized is not None:
                return deserialized
        
        if isinstance(value, GenericSerializedValue):
            return value.serialized_value
        
        return value

    """
    Private methods
    """
    @classmethod
    def _get_enumerator(cls, value: dict | BaseModel):
        if isinstance(value, dict):
            for key, item_value in value.items():
                yield key, type(item_value), item_value
        elif isinstance(value, BaseModel):
            for name, field in value.model_fields.items():
                yield name, cls._get_property_type(field), getattr(value, name)
    
    @classmethod
    def _should_serialize(cls, value: Any, type_hint: Any) -> bool:
        if isinstance(value, dict) or isinstance(value, BaseModel):
            return True
        
        if is_dict_type(type_hint) or is_pydantic_model(type_hint):
            return True
        
        return False
    
    @classmethod
    def _should_deserialize(cls, type_hint: Any) -> bool:        
        if is_dict_type(type_hint) or is_pydantic_model(type_hint):
            return True
        
        return False
    
    @classmethod
    def _get_property_type(cls, field: FieldInfo) -> Any:
        annotation = field._attributes_set.get("annotation", None)
        if annotation is None:
            return field.annotation
        
        return annotation
    
    @classmethod
    def _default_deserialized_model(cls, value, type_hint: Any) -> Any:
        if is_dict_type(type_hint):
            return value
        elif is_pydantic_model(type_hint):
            return type_hint.model_construct(**value)
        
        return value
    
    @classmethod
    def _get_attribute(cls, value: Any, name: str) -> Any:
        if isinstance(value, BaseModel):
            return getattr(value, name)
        elif isinstance(value, dict):
            return value[name]
        else:
            raise ValueError(f"Invalid value type: {type(value)}")
    
    @classmethod
    def _set_attribute(cls, model: Any, name: str, value: Any):
        if isinstance(model, BaseModel):
            setattr(model, name, value)
        elif isinstance(model, dict):
            model[name] = value
        else:
            raise ValueError(f"Invalid model type: {type(model)}")
