from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from typing import Any, Union, TypeVar
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
class UnionType:
    arg_type: Any
    bound_type: Any

class UnionTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = self._should_transform
        self.should_deserialize = self._should_transform

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        serialized_value = Transformer.serialize(value, type(value))
        if serialized_value is not None:
            return GenericSerializedValue(
                serialized_value=serialized_value,
                serialized_type_hint=get_fqn(type(value))
            )

        return None
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        serialized_value = GenericSerializedValue.model_validate(value)
        value_to_deserialize = serialized_value.serialized_value
        type_hint_to_deserialize = get_reference_from_fqn(serialized_value.serialized_type_hint)
        return Transformer.deserialize(value_to_deserialize, type_hint_to_deserialize)
    
    def _should_transform(self, value: Any, type_hint: Any) -> bool:
        type_hint_origin = getattr(type_hint, "__origin__", None)
        if type_hint_origin == Union:
            return True
        
        type_of_value = type(value)
        origin_of_type_of_value = getattr(type_of_value, "__origin__", None)
        if origin_of_type_of_value == Union:
            return True
        
        return False
