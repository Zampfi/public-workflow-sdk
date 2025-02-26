from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from typing import Any
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue

class DictTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = self._should_transform
        self.should_deserialize = self._should_transform

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        serialized_dict = {}
        type_hint_dict = {}
        for key, value in value.items():
            value_type = type(value)
            serialized_dict[key] = Transformer.serialize(value, value_type)
            type_hint_dict[key] = get_fqn(value_type)

        return GenericSerializedValue(
            serialized_value=serialized_dict,
            serialized_type_hint=type_hint_dict
        ).model_dump()

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        generic_serialized_value = GenericSerializedValue.model_validate(value)
        value: dict = generic_serialized_value.serialized_value
        type_hint: dict = generic_serialized_value.serialized_type_hint

        deserialized_dict = {}
        for key, value in value.items():
            deserialized_dict[key] = Transformer.deserialize(value, get_reference_from_fqn(type_hint[key]))

        return deserialized_dict

    def _should_transform(self, value: Any, type_hint: Any) -> bool:
        args = getattr(type_hint, "__args__", None)
        return isinstance(value, dict) or type_hint is dict or \
            getattr(type_hint, "__origin__", None) == dict
            #(args is not None and len(args) == 2 and args[0] is str)