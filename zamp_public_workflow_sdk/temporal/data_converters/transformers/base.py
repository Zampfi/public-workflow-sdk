from abc import ABC, abstractmethod
from typing import Any, Callable

class BaseTransformer(ABC):
    should_serialize: Callable[[Any], bool]
    should_deserialize: Callable[[Any, Any], bool]

    def serialize(self, value: Any) -> Any:
        if self.should_serialize(value):
            return self._serialize_internal(value)
        
        return None

    def deserialize(self, value: Any, type_hint: Any) -> Any:
        if self.should_deserialize(value, type_hint):
            return self._deserialize_internal(value, type_hint)
        
        return None

    @abstractmethod
    def _serialize_internal(self, value: Any) -> Any:
        pass

    @abstractmethod
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        pass