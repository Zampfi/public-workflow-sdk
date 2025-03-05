from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from pydantic._internal._model_construction import ModelMetaclass
from pydantic import BaseModel
from typing import Any

class PydanticModelMetaclassTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value: isinstance(value, ModelMetaclass)
        self.should_deserialize = lambda value, type_hint: False

    def _serialize_internal(self, value: Any) -> Any:
        return str(value)

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        return None