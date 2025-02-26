from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from typing import Any, Callable
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn, get_reference_from_fqn
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue

class ListTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize: Callable[[Any, Any], bool] = self._should_transform
        self.should_deserialize: Callable[[Any, Any], bool] = self._should_transform

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        serialized_items = []
        generic_type_hints = []

        args = getattr(type_hint, "__args__", None)
        bound = getattr(type_hint, "__bound__", None)
        list_item_type_hint = None
        if args is not None and len(args) > 0:
            list_item_type_hint = args[0]

        is_all_items_same_type = True
        for item in value:
            serialized_items.append(Transformer.serialize(item, type(item)))
            generic_type_hints.append(get_fqn(type(item)))
            if type(item) != list_item_type_hint:
                is_all_items_same_type = False

        return GenericSerializedValue(
            serialized_value=serialized_items, 
            serialized_type_hint=get_fqn(list_item_type_hint) if is_all_items_same_type else generic_type_hints
        ).model_dump()

    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        try:
            generic_serialized_value = GenericSerializedValue.model_validate(value)
            value: list = generic_serialized_value.serialized_value
            type_hint = generic_serialized_value.serialized_type_hint
        except:
            type_hint = getattr(type_hint, "__args__", None)
            if type_hint is not None and len(type_hint) > 0:
                type_hint = type_hint[0]

        deserialized_items = []

        if isinstance(type_hint, list):
            for item, type_hint in zip(value, type_hint):
                deserialized_item = Transformer.deserialize(item, get_reference_from_fqn(type_hint))
                if deserialized_item is not None:
                    deserialized_items.append(deserialized_item)
        else:
            for item in value:
                deserialized_item = Transformer.deserialize(item, get_reference_from_fqn(type_hint))
                if deserialized_item is not None:
                    deserialized_items.append(deserialized_item)

        return deserialized_items

    def _should_transform(self, value: Any, type_hint: Any) -> bool:
        return isinstance(value, list) or type_hint is list or \
            getattr(type_hint, "__origin__", None) == list or \
            getattr(type_hint, "__class__", None) == list