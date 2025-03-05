from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.base import BaseCollectionsTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue
from typing import Any

class TupleTransformer(BaseCollectionsTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value: isinstance(value, tuple)
        self.should_deserialize = lambda value, type_hint: type_hint is tuple

    def _serialize_internal(self, value: Any) -> GenericSerializedValue:
        serialized_items = []
        generic_type_hints = []
        for item in value:
            serialized_value = Transformer.serialize(item)
            serialized_items.append(serialized_value.serialized_value)
            generic_type_hints.append(serialized_value.serialized_type_hint)

        return GenericSerializedValue(
            serialized_value=serialized_items, 
            serialized_type_hint=get_fqn(tuple),
            serialized_individual_type_hints=generic_type_hints
        )

    def _deserialize_internal(self, value: Any, type_hint: type, individual_type_hints: list[type]) -> Any:
        deserialized_items = []
        for item, item_type_hint in zip(value, individual_type_hints):
            deserialized_item = Transformer.deserialize(item, item_type_hint)
            if deserialized_item is not None:
                deserialized_items.append(deserialized_item)

        return tuple(deserialized_items)