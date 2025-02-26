from pydantic import BaseModel
from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from typing import Any
class NoneTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value, type_hint: value is None
        self.should_deserialize = lambda value, type_hint: type_hint == type(None)

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        return "None"

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        return None