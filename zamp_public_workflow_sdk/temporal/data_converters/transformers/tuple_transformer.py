from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from typing import Any
class TupleTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = self._should_transform
        self.should_deserialize = self._should_transform

    def _should_transform(self, value, type_hint) -> bool:
        return type_hint is tuple

    def _serialize_internal(self, value, type_hint) -> Any:
        serialized_items = []
        generic_type_hints = []
        for item in value:
            serialized_items.append(Transformer.serialize(item, type(item)))
            generic_type_hints.append(get_fqn(type(item)))

        return GenericSerializedValue(
            serialized_value=serialized_items, 
            serialized_type_hint=generic_type_hints
        ).model_dump()

    def _deserialize_internal(self, value, type_hint) -> Any:
        try:
            generic_serialized_value = GenericSerializedValue.model_validate(value)
            value: list = generic_serialized_value.serialized_value
            new_type_hint = generic_serialized_value.serialized_type_hint
        except:
            new_type_hint = dict

        deserialized_items = []
        if isinstance(new_type_hint, list):
            for item, item_type_hint in zip(value, new_type_hint):
                deserialized_item = Transformer.deserialize(item, get_reference_from_fqn(item_type_hint))
                if deserialized_item is not None:
                    deserialized_items.append(deserialized_item)
        else:
            for item in value:
                deserialized_item = Transformer.deserialize(item, get_reference_from_fqn(new_type_hint))
                if deserialized_item is not None:
                    deserialized_items.append(deserialized_item)

        return tuple(deserialized_items)