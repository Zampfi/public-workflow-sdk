from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from typing import Union
from typing import Any, Callable
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, safe_issubclass
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer

class UnionTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize: Callable[[Any], bool] = lambda value: False
        self.should_deserialize: Callable[[Any, Any], bool] = lambda value, type_hint: self._should_deserialize_internal(value, type_hint)
    
    def _serialize_internal(self, value: Any) -> Any:
        return None

    def _should_deserialize_internal(self, value: Any, type_hint: Any) -> bool:
        if type_hint:
            try:
                if type_hint.__origin__ is Union:
                    return True
            except:
                pass
        
        return False
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        args = type_hint.__args__
        for arg in args:
            if not arg:
                # Value == None is already checked at the transformer level, not repeating it here.
                continue
            
            try:
                value = Transformer.deserialize(value, arg)
                if value is not None:
                    return value
                
            except Exception as e:
                continue

        return None