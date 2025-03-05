from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from datetime import datetime, date
from typing import Any, Callable
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn

class DateTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize: Callable[[Any], bool] = lambda value: isinstance(value, datetime) or isinstance(value, date)
        self.should_deserialize: Callable[[Any, Any], bool] = lambda value, type_hint: type_hint is datetime or type_hint is date

    def _serialize_internal(self, value: Any) -> Any:
        return GenericSerializedValue(
            serialized_value=value.isoformat(),
            serialized_type_hint=get_fqn(type(value))
        )
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> datetime:
        if type_hint is datetime:
            return datetime.fromisoformat(value)
        
        return date.fromisoformat(value)
