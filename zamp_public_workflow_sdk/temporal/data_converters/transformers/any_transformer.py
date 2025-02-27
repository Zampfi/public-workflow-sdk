from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
from typing import Any

class AnyTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = self._should_transform
        self.should_deserialize = self._should_transform

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        type_of_value = type(value)
        return GenericSerializedValue(
            serialized_value=Transformer.serialize(value, type_of_value),
            serialized_type_hint=get_fqn(type_of_value)
        ).model_dump()
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        serialized_value = GenericSerializedValue.model_validate(value)
        return Transformer.deserialize(serialized_value.serialized_value, get_reference_from_fqn(serialized_value.serialized_type_hint))
    
    def _should_transform(self, value: Any, type_hint: Any) -> bool:
        return type_hint == Any