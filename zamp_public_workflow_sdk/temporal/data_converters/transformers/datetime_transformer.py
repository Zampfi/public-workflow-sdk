from temporalio import workflow
from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from datetime import datetime, date
from typing import Any, Callable
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, safe_issubclass

class DateTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize: Callable[[Any], bool] = lambda value: isinstance(value, datetime) or isinstance(value, date)
        self.should_deserialize: Callable[[Any, Any], bool] = lambda value, type_hint: self._should_deserialize_internal(value, type_hint)

    def _serialize_internal(self, value: Any) -> Any:
        return GenericSerializedValue(
            serialized_value=value.isoformat(),
            serialized_type_hint=get_fqn(type(value))
        )
    
    def _should_deserialize_internal(self, value: Any, type_hint: Any) -> bool:
        if type_hint:
            return safe_issubclass(type_hint, datetime) or safe_issubclass(type_hint, date)
        
        return False
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> datetime:
        if issubclass(type_hint, datetime):
            return datetime.fromisoformat(value)
        
        return date.fromisoformat(value)
