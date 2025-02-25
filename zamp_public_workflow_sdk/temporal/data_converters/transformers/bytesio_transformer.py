from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from typing import Any
from io import BytesIO

class BytesIOTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value, type_hint: isinstance(value, BytesIO) or type_hint is BytesIO
        self.should_deserialize = lambda value, type_hint: type_hint is BytesIO

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        return value.getvalue()
    
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        return BytesIO(value)