from zamp_public_workflow_sdk.temporal.data_converters.transformers.base import BaseTransformer
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing import Any
from pydantic.json_schema import to_jsonable_python
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer

class PydanticTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.should_serialize = lambda value, type_hint: isinstance(value, BaseModel) or type_hint is BaseModel
        self.should_deserialize = lambda value, type_hint: self._should_deserialize_internal(value, type_hint)

    def _serialize_internal(self, value: Any, type_hint: Any) -> Any:
        try:
            dict_obj = to_jsonable_python(value)
        except Exception:
            dict_obj = value.model_dump(warnings=False)

        for name, field in value.model_fields.items():
            property_type = field.annotation
            property_value = getattr(value, name)
            property_serialized = Transformer.serialize(property_value, property_type)
            if property_serialized is not None:
                dict_obj[name] = property_serialized

        return dict_obj
        
    def _deserialize_internal(self, value: Any, type_hint: Any) -> Any:
        pydantic_model = type_hint.model_construct(**value)
        for name, field in pydantic_model.model_fields.items():
            field_annotation = field.annotation
            deserialized_value = Transformer.deserialize(value[name], field_annotation)
            if deserialized_value is not None:
                setattr(pydantic_model, name, deserialized_value)

        return pydantic_model
    
    def _should_deserialize_internal(self, value: Any, type_hint: Any) -> bool:
        if type_hint is BaseModel:
            return True
        
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            return True

        return False