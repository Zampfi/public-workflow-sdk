from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from typing import Any
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
from typing import TypeVar
from pydantic import BaseModel
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer

class PydanticTypeVarTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value, type_hint: self.is_base_model_type_var(type_hint)
        self.should_deserialize = lambda value, type_hint: self.is_base_model_type_var(type_hint)

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        property_class = value.__class__
        return GenericSerializedValue(
            serialized_value=Transformer.serialize(value, property_class),
            serialized_type_hint=get_fqn(property_class)
        ).model_dump()

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        generic_serialized_value = GenericSerializedValue.model_validate(value)
        value = generic_serialized_value.serialized_value
        type_hint = get_reference_from_fqn(generic_serialized_value.serialized_type_hint)
        return Transformer.deserialize(value, type_hint)

    def is_base_model_type_var(self, annotation) -> bool:
        if annotation.__class__ is TypeVar and annotation.__bound__ is BaseModel:
            return True

        if getattr(annotation, "__class__", None) is TypeVar and getattr(annotation, "__bound__", None) is BaseModel:
            return True

        return False