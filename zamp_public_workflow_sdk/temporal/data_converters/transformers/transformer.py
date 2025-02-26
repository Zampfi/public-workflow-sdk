from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from typing import Any
from pydantic_core import to_jsonable_python
import json

class Transformer:
    _transformers: list[BaseTransformer] = []

    @classmethod
    def register_transformer(cls, transformer: BaseTransformer):
        cls._transformers.append(transformer)

    @classmethod
    def serialize(cls, value, type_hint: Any=None) -> Any:
        if value is None:
            return value
        
        for transformer in cls._transformers:
            serialized = transformer.serialize(value, type_hint)
            if serialized is not None:
                return serialized
            
        return to_jsonable_python(value)

    @classmethod
    def deserialize(cls, value: Any, type_hint: Any) -> Any:
        if type_hint is None or value is None:
            return value
                
        for transformer in cls._transformers:
            deserialized = transformer.deserialize(value, type_hint)
            if deserialized is not None:
                return deserialized
            
        return value