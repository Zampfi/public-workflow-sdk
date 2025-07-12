from typing import Any, Dict
from pydantic import BaseModel
from pydantic_core import to_jsonable_python
from pydantic.fields import FieldInfo
import logging

from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.base import BaseCollectionsTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import (
    get_type_field_name,
    get_fqn,
    is_dict_type,
    is_pydantic_model,
    get_individual_type_field_name,
    is_type_field,
    get_reference_from_fqn,
)

logger = logging.getLogger(__name__)


class Transformer:
    _transformers: list[BaseTransformer] = []
    _collection_transformers: list[BaseCollectionsTransformer] = []

    @classmethod
    def register_transformer(cls, transformer: BaseTransformer):
        cls._transformers.append(transformer)

    @classmethod
    def register_collection_transformer(cls, transformer: BaseCollectionsTransformer):
        cls._collection_transformers.append(transformer)

    @classmethod
    def serialize(cls, value: Any) -> GenericSerializedValue:
        if value is None:
            return GenericSerializedValue(
                serialized_value=None,
                serialized_type_hint=get_fqn(type(value))
            )

        # Fast path for Pydantic models
        if isinstance(value, BaseModel):
            try:
                return GenericSerializedValue(
                    serialized_value=to_jsonable_python(value),
                    serialized_type_hint=get_fqn(type(value))
                )
            except Exception as e:
                logger.warning(f"Failed to serialize Pydantic model {type(value).__name__}: {e}")
                pass  # fallback to full logic below

        for collection_transformer in cls._collection_transformers:
            serialized = collection_transformer.serialize(value)
            if serialized is not None:
                return serialized

        if cls._should_serialize(value):
            try:
                serialized_result = {}
                for item_key, item_type, item_value in cls._get_enumerator(value):
                    serialized = cls.serialize(item_value)
                    if isinstance(serialized, GenericSerializedValue):
                        serialized_result[item_key] = serialized.serialized_value
                        serialized_result[get_type_field_name(item_key)] = serialized.serialized_type_hint
                        if serialized.serialized_individual_type_hints is not None:
                            serialized_result[get_individual_type_field_name(item_key)] = serialized.serialized_individual_type_hints
                    else:
                        serialized_result[item_key] = serialized
                return GenericSerializedValue(
                    serialized_value=serialized_result,
                    serialized_type_hint=get_fqn(type(value))
                )
            except Exception as e:
                logger.warning(f"Failed to serialize object {type(value).__name__} with recursive logic: {e}")
                pass  # fallback to custom transformers

        for transformer in cls._transformers:
            try:
                serialized = transformer.serialize(value)
                if serialized is not None:
                    return serialized
            except Exception as e:
                logger.warning(f"Failed to serialize with transformer {type(transformer).__name__}: {e}")
                continue

        # Fallback
        return GenericSerializedValue(
            serialized_value=to_jsonable_python(value),
            serialized_type_hint=get_fqn(type(value))
        )

    @classmethod
    def deserialize(
        cls,
        value: Any,
        type_hint: type,
        individual_type_hints: list[type] | None = None
    ) -> Any:
        if type_hint is None or value is None:
            return value

        # Fast path for Pydantic model reconstruction
        if is_pydantic_model(type_hint) and isinstance(value, dict):
            try:
                return type_hint.model_construct(**value)
            except Exception as e:
                logger.warning(f"Failed to deserialize Pydantic model {type_hint.__name__}: {e}")
                pass  # fallback to recursive

        for collection_transformer in cls._collection_transformers:
            try:
                deserialized = collection_transformer.deserialize(value, type_hint, individual_type_hints)
                if deserialized is not None:
                    return deserialized
            except Exception as e:
                logger.warning(f"Failed to deserialize with collection transformer {type(collection_transformer).__name__}: {e}")
                continue

        if cls._should_deserialize(type_hint):
            try:
                deserialized_result = cls._default_deserialized_model(value, type_hint)

                for item_key, item_type, item_value in cls._get_enumerator(deserialized_result):
                    if is_type_field(item_key):
                        continue

                    type_key = get_type_field_name(item_key)
                    if type_key in value:
                        try:
                            item_type = get_reference_from_fqn(cls._get_attribute(value, type_key))
                        except Exception as e:
                            logger.warning(f"Failed to get type reference for field {item_key}: {e}")
                            pass

                    individual_type_hints_key = get_individual_type_field_name(item_key)
                    if individual_type_hints_key in value:
                        try:
                            raw_hints = cls._get_attribute(value, individual_type_hints_key)
                            individual_type_hints = [get_reference_from_fqn(hint) for hint in raw_hints]
                        except Exception as e:
                            logger.warning(f"Failed to get individual type hints for field {item_key}: {e}")
                            individual_type_hints = None

                    raw_value = cls._get_attribute(value, item_key)

                    # Primitive fast path
                    if isinstance(raw_value, (int, float, str, bool)) or raw_value is None:
                        deserialized = raw_value
                    else:
                        deserialized = cls.deserialize(raw_value, item_type, individual_type_hints)

                    cls._set_attribute(deserialized_result, item_key, deserialized)

                return cls._delete_type_keys(deserialized_result)

            except Exception as e:
                logger.warning(f"Failed to deserialize object {type_hint.__name__} with recursive logic: {e}")
                pass  # fallback to custom transformers

        for transformer in cls._transformers:
            try:
                deserialized = transformer.deserialize(value, type_hint)
                if deserialized is not None:
                    return deserialized
            except Exception as e:
                logger.warning(f"Failed to deserialize with transformer {type(transformer).__name__}: {e}")
                continue

        return value

    # -------------------------------
    # Private helper methods
    # -------------------------------

    @classmethod
    def _delete_type_keys(cls, value: dict):
        if isinstance(value, dict):
            keys_to_delete = [k for k in value.keys() if is_type_field(k)]
            for key in keys_to_delete:
                del value[key]
        return value

    @classmethod
    def _get_enumerator(cls, value: dict | BaseModel):
        if isinstance(value, dict):
            for key, item_value in value.items():
                yield key, type(item_value), item_value
        elif isinstance(value, BaseModel):
            for name, field in value.model_fields.items():
                yield name, cls._get_property_type(field), getattr(value, name)

    @classmethod
    def _should_serialize(cls, value: Any) -> bool:
        return isinstance(value, (dict, BaseModel))

    @classmethod
    def _should_deserialize(cls, type_hint: Any) -> bool:
        return is_dict_type(type_hint) or is_pydantic_model(type_hint)

    @classmethod
    def _get_property_type(cls, field: FieldInfo) -> Any:
        return field._attributes_set.get("annotation") or field.annotation

    @classmethod
    def _default_deserialized_model(cls, value, type_hint: Any) -> Any:
        if is_dict_type(type_hint):
            return value
        elif is_pydantic_model(type_hint):
            if isinstance(value, type_hint):
                return value
            return type_hint.model_construct(**value)
        return value

    @classmethod
    def _get_attribute(cls, value: Any, name: str) -> Any:
        if isinstance(value, BaseModel):
            return getattr(value, name)
        elif isinstance(value, dict):
            return value[name]
        raise ValueError(f"Invalid value type: {type(value)}")

    @classmethod
    def _set_attribute(cls, model: Any, name: str, value: Any):
        if isinstance(model, BaseModel):
            setattr(model, name, value)
        elif isinstance(model, dict):
            model[name] = value
        else:
            raise ValueError(f"Invalid model type: {type(model)}")
