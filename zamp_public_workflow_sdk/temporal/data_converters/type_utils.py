import importlib
from typing import TypeVar
from pydantic import BaseModel
from pydantic.fields import FieldInfo

def get_fqn(cls):
    if cls == type(None):
        return "None"

    if cls.__module__ == "builtins":
        return cls.__name__

    return f"{cls.__module__}.{cls.__name__}"

def get_reference_from_fqn(fqn: str):
    if fqn == "None":
        return type(None)

    # Handle built-in types
    if "." not in fqn:
        if fqn in __builtins__:
            return __builtins__[fqn]
    
    # Handle fully qualified names
    module_name, class_name = fqn.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

def _is_base_model_type_var(field: FieldInfo) -> bool:
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

def get_annotation_type_field(field_name: str) -> str:
    return "__" + field_name + "_type"
    
def safe_issubclass(obj, cls):
    if isinstance(obj, type):
        return issubclass(obj, cls)
    return False