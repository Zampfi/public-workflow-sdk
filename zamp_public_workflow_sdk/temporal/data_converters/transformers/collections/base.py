from abc import ABC, abstractmethod
from typing import Any, Callable
from zamp_public_workflow_sdk.temporal.data_converters.transformers.models import GenericSerializedValue

class BaseCollectionsTransformer(ABC):
    should_serialize: Callable[[Any], bool]
    should_deserialize: Callable[[Any, Any], bool]

    def serialize(self, value: Any) -> GenericSerializedValue | None:
        if not self.should_serialize(value):
            return None
        
        return self._serialize_internal(value)
    
    def deserialize(self, value: Any, type_hint: Any, individual_type_hints: list[type]=None) -> Any:
        if not self.should_deserialize(value, type_hint):
            return None
        
        return self._deserialize_internal(value, type_hint, individual_type_hints)

    @abstractmethod
    def _serialize_internal(self, value: Any) -> Any:
        pass

    @abstractmethod
    def _deserialize_internal(self, value: Any, type_hint: Any, individual_type_hints: list[type]=None) -> Any:
        pass