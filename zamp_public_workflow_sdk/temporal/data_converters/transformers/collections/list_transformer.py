from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.base import BaseCollectionsTransformer
from typing import Any, Callable
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn, get_inner_type
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue

class ListTransformer(BaseCollectionsTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize: Callable[[Any], bool] = lambda value: isinstance(value, list)
        self.should_deserialize: Callable[[Any, Any], bool] = lambda value, type_hint: type_hint is list or getattr(type_hint, "__origin__", None) == list

    def _serialize_internal(self, value: Any) -> GenericSerializedValue:
        serialized_items = []
        individual_type_hints: list[str] = []

        for item in value:
            serialized_value = Transformer.serialize(item)
            serialized_items.append(serialized_value.serialized_value)
            if serialized_value.serialized_individual_type_hints is not None:
                individual_type_hints.extend(serialized_value.serialized_individual_type_hints)
            else:
                individual_type_hints.append(serialized_value.serialized_type_hint)

        serialized_value = GenericSerializedValue(
            serialized_value=serialized_items,
            serialized_type_hint=get_fqn(self._get_serialized_type_hint(individual_type_hints)),
        )
        
        # If all the individual type hints are the same, we can return the serialized value
        if not self._is_homogeneous(individual_type_hints):
            serialized_value.serialized_individual_type_hints = individual_type_hints
        
        return serialized_value
    
    def _deserialize_internal(self, value: Any, type_hint: type, individual_type_hints: list[type]) -> Any:
        deserialized_items = []

        if individual_type_hints is not None and len(individual_type_hints) > 0:
            for item, item_type_hint in zip(value, individual_type_hints):
                deserialized_item = Transformer.deserialize(item, item_type_hint)
                if deserialized_item is not None:
                    deserialized_items.append(deserialized_item)
        else:
            for item in value:
                deserialized_item = Transformer.deserialize(item, get_inner_type(type_hint))
                if deserialized_item is not None:
                    deserialized_items.append(deserialized_item)

        return deserialized_items
    
    def _get_serialized_type_hint(self, serialized_individual_type_hints: list[str]) -> type:
        if len(serialized_individual_type_hints) == 0:
            return list
        
        if self._is_homogeneous(serialized_individual_type_hints):
            return list[get_reference_from_fqn(serialized_individual_type_hints[0])]

        return list
    
    def _is_homogeneous(self, serialized_individual_type_hints: list[str]) -> bool:
        return all(individual_type_hint == serialized_individual_type_hints[0] for individual_type_hint in serialized_individual_type_hints)