import importlib
from typing import Any
from pydantic import BaseModel
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

def get_type_field_name(field_name: str) -> str:
    return "__" + field_name + "_type"
    
def safe_issubclass(obj, cls):
    if isinstance(obj, type):
        return issubclass(obj, cls)
    return False

def is_dict_type(type_hint: Any) -> bool:
    return type_hint is dict or getattr(type_hint, '__origin__', None) is dict

def is_pydantic_model(type_hint: Any) -> bool:
    return safe_issubclass(type_hint, BaseModel)