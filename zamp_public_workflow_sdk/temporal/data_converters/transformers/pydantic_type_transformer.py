from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
from pydantic import BaseModel
from typing import Any

class PydanticTypeTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = self._should_transform
        self.should_deserialize = self._should_transform

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        return get_fqn(value)

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        return get_reference_from_fqn(value)
    
    def _should_transform(self, value: Any, type_hint: Any) -> bool:
        is_type_hint_type = type_hint is type and issubclass(type_hint, BaseModel)
        is_origin_type = getattr(type_hint, "__origin__", None) is type
        args = getattr(type_hint, "__args__", None)
        is_args_type = args is not None and len(args) > 0 and isinstance(args[0], type) and issubclass(args[0], BaseModel)
        return is_type_hint_type or (is_origin_type and is_args_type)
