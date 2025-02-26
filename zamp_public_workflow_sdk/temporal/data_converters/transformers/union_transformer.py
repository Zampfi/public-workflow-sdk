from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from typing import Any, Union

class UnionTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = self._should_transform
        self.should_deserialize = self._should_transform

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        inner_types = self._get_inner_types(type_hint)
        if len(inner_types) == 0:
            return None
        
        for inner_type in inner_types:
            serialized_value = Transformer.serialize(value, inner_type)
            if serialized_value is not None:
                return serialized_value
            
        return None
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        inner_types = self._get_inner_types(type_hint)
        if len(inner_types) == 0:
            return None
        
        for inner_type in inner_types:
            deserialized_value = Transformer.deserialize(value, inner_type)
            if deserialized_value is not None:
                return deserialized_value

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
    
    def _get_inner_types(self, type_hint: Any) -> list[Any]:
        return getattr(type_hint, "__args__", None)