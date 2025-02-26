import base64
import importlib
from io import BytesIO
import json
from pydantic import BaseModel
from pydantic_core import to_jsonable_python, from_json
from pydantic.fields import FieldInfo
from pydantic._internal._model_construction import ModelMetaclass
from temporalio.api.common.v1 import Payload
from temporalio.converter import CompositePayloadConverter, JSONPlainPayloadConverter, DefaultPayloadConverter
from typing import Any, Type, Optional, TypeVar
from datetime import datetime
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.list_transformer import ListTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.dict_transformer import DictTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytes_transformer import BytesTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytesio_transformer import BytesIOTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_model_metaclass_transformer import PydanticModelMetaclassTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_transformer import PydanticTypeTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_var_transformer import PydanticTypeVarTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_transformer import PydanticTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.union_transformer import UnionTransformer
def get_fqn(cls):
    if cls.__module__ == "builtins":
        return cls.__name__

    return f"{cls.__module__}.{cls.__name__}"

def get_reference_from_fqn(fqn: str):
    module_name, class_name = fqn.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def is_base_model_type_var(field: FieldInfo) -> bool:
    if (
        field.annotation.__class__ is TypeVar
        and field.annotation.__bound__ is BaseModel
    ):
        return True

    if field._attributes_set.get("annotation") is not None:
        annotations_attribute_set = field._attributes_set.get("annotation")
        if getattr(annotations_attribute_set, "__class__", None) is TypeVar and getattr(annotations_attribute_set, "__bound__", None) is BaseModel:
            return True

        # Check if the field is a list of BaseModel
        if getattr(annotations_attribute_set, "__origin__", None) is list and getattr(annotations_attribute_set, "__args__", None) is not None:
            if getattr(annotations_attribute_set.__args__[0], "__bound__", None) is BaseModel:
                return True

    return False

def check_basic_types(o):
    if isinstance(o, type) and issubclass(o, BaseModel):
        return get_fqn(o)
    
    if issubclass(o.__class__, ModelMetaclass):
        return str(o)
    
    if o.__class__ is BytesIO:
        return base64.b64encode(o.getvalue()).decode("ascii")

    if o.__class__ is bytes:
        return base64.b64encode(o).decode("ascii")
    
    return None

def custom_model_dump(o):
    basic_type = check_basic_types(o)
    if basic_type is not None:
        return basic_type

    d = {}
    try:
        d = to_jsonable_python(o)
    except Exception:
        d = o.model_dump(warnings=False)

    if isinstance(o, BaseModel):
        for name, field in o.model_fields.items():
            property_type = field.annotation
            property_value = getattr(o, name)
            
            if is_base_model_type_var(field):
                if getattr(property_type, "__origin__", None) == list or getattr(property_type, "__class__", None) == list:
                    d["__" + name + "_type"] = [get_fqn(item.__class__) for item in property_value]
                    d[name] = [item.model_dump() for item in property_value]
                else:
                    d["__" + name + "_type"] = get_fqn(property_value.__class__)
                    d[name] = property_value.model_dump()

                continue

            if property_type is type and issubclass(property_type, BaseModel):
                d[name] = get_fqn(property_value)
                continue

            if issubclass(getattr(property_type, "__class__", None), BaseModel):
                d[name] = custom_model_dump(property_value)
                continue

            if getattr(property_type, "__origin__", None) == list or getattr(property_type, "__class__", None) == list:
                args = getattr(property_type, "__args__", None)
                if len(args) > 0 and issubclass(args[0] , BaseModel):
                    d[name] = [custom_model_dump(item) for item in property_value]
                    continue

            if property_type is BytesIO:
                d[name] = base64.b64encode(property_value.getvalue()).decode("ascii")
                continue

            if property_type is bytes:
                d[name] = base64.b64encode(property_value).decode("ascii")
                continue

            if property_type is datetime:
                d[name] = property_value.isoformat()
                continue

    return d

def custom_model_validate(obj, type_hint):
    pydantic_model = type_hint.model_construct(**obj)
    for name, field in pydantic_model.model_fields.items():
        field_annotation = field.annotation
        field_class = field_annotation.__class__
        field_origin = getattr(field_annotation, "__origin__", None)
        field_args = getattr(field_annotation, "__args__", None)
        first_arg = field_args[0] if field_args and len(field_args) > 0 else None
        
        if is_base_model_type_var(field):
            type_field_name = "__" + name + "_type"
            if type_field_name in obj:
                obj_type = obj.pop(type_field_name)
            if obj_type.__class__ == list:
                list_obj = []
                for item_type, item_value in zip(obj_type, obj[name]):
                    list_obj.append(custom_model_validate(item_value, get_reference_from_fqn(item_type)))
                setattr(pydantic_model, name, list_obj)
            else:
                setattr(pydantic_model, name, custom_model_validate(obj[name], get_reference_from_fqn(obj_type)))

            continue

        if field_origin is type and first_arg is BaseModel:
            setattr(pydantic_model, name, get_reference_from_fqn(obj[name]))
            continue

        if issubclass(field_class, BaseModel):
            setattr(pydantic_model, name, custom_model_validate(obj[name], field_class))
            continue

        if field_origin == list or field_class == list:
            first_arg_bound = getattr(first_arg, "__bound__", None) if first_arg else None
            if first_arg_bound is BaseModel:
                list_base_model_type = "__" + name + "_type"
                if list_base_model_type in obj:
                    setattr(pydantic_model, name, [custom_model_validate(item, list_base_model_type) for item in obj[name]])

            if isinstance(first_arg, type) and issubclass(first_arg, BaseModel):
                setattr(pydantic_model, name, [custom_model_validate(item, first_arg) for item in obj[name]])
                                
        if field_annotation is bytes:
            setattr(pydantic_model, name, base64.b64decode(obj[name]))

        if field_annotation is BytesIO:
            setattr(pydantic_model, name, BytesIO(base64.b64decode(obj[name])))

        if field_annotation is datetime:
            setattr(pydantic_model, name, datetime.fromisoformat(obj[name]))

    return pydantic_model

class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """
    def __init__(self):
        super().__init__()
        Transformer.register_transformer(PydanticTypeTransformer())
        Transformer.register_transformer(PydanticTypeVarTransformer())
        Transformer.register_transformer(PydanticModelMetaclassTransformer())
        Transformer.register_transformer(PydanticTransformer())
        Transformer.register_transformer(ListTransformer())
        Transformer.register_transformer(DictTransformer())
        Transformer.register_transformer(BytesTransformer())
        Transformer.register_transformer(BytesIOTransformer())
        Transformer.register_transformer(UnionTransformer())
        
    def to_payload(self, value: Any) -> Optional[Payload]:        
        json_data = json.dumps(value, separators=(",", ":"), sort_keys=True, default=lambda x: Transformer.serialize(x))
        return Payload(
            metadata={"encoding": self.encoding.encode()},
            data=json_data.encode(),
        )

    def from_payload(self, payload: Payload, type_hint: Type | None = None) -> Any:
        obj = from_json(payload.data)
        return Transformer.deserialize(obj, type_hint)
    
class PydanticPayloadConverter(CompositePayloadConverter):
    """Payload converter that replaces Temporal JSON conversion with Pydantic
    JSON conversion.
    """

    def __init__(self) -> None:
        super().__init__(
            *(
                (
                    c
                    if not isinstance(c, JSONPlainPayloadConverter)
                    else PydanticJSONPayloadConverter()
                )
                for c in DefaultPayloadConverter.default_encoding_payload_converters
            )
        )