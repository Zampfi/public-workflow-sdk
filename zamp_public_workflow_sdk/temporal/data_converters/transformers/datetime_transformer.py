from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from datetime import datetime, date
from typing import Any, Callable

class DateTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize: Callable[[Any, Any], bool] = lambda value, type_hint: isinstance(value, datetime) or isinstance(value, date) or type_hint is datetime or type_hint is date
        self.should_deserialize: Callable[[Any, Any], bool] = lambda value, type_hint: type_hint is datetime or type_hint is date

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        return value.isoformat()
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> datetime:
        if type_hint is datetime:
            return datetime.fromisoformat(value)
        
        return date.fromisoformat(value)
