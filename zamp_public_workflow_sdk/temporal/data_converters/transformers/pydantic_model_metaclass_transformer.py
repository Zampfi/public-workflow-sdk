from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic._internal._model_construction import ModelMetaclass

from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import \
    BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import \
    GenericSerializedValue
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import (
    get_fqn, get_reference_from_fqn)


class PydanticModelMetaclassTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value: isinstance(value, ModelMetaclass)
        self.should_deserialize = lambda value, type_hint: False

    def _serialize_internal(self, value: Any) -> Any:
        return GenericSerializedValue(
            serialized_value=get_fqn(value),
            serialized_type_hint=get_fqn(type(value))
        )

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        return None
