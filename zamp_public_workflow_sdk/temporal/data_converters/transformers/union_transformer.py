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
        return Transformer._serialize(value, type(value))
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        if isinstance(value, GenericSerializedValue):
            return Transformer.deserialize(value, type(value.serialized_value))
        
        return None
    
    def _should_transform(self, value: Any, type_hint: Any) -> bool:
        type_hint_origin = getattr(type_hint, "__origin__", None)
        if type_hint_origin == Union:
            return True
        
        type_of_value = type(value)
        origin_of_type_of_value = getattr(type_of_value, "__origin__", None)
        if origin_of_type_of_value == Union:
            return True
        
        return False
