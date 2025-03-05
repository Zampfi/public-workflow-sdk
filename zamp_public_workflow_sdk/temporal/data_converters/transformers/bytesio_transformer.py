from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn
from typing import Any
import base64
from io import BytesIO

class BytesIOTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value: isinstance(value, BytesIO) 
        self.should_deserialize = lambda value, type_hint: type_hint is BytesIO

    def _serialize_internal(self, value: Any) -> Any:
        return GenericSerializedValue(
            serialized_value=base64.b64encode(value.getvalue()).decode("utf-8"),
            serialized_type_hint=get_fqn(BytesIO)
        )

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        return BytesIO(base64.b64decode(value))