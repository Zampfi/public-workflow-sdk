from pydantic import BaseModel
from typing import Any

class GenericSerializedValue(BaseModel):
    serialized_value: Any
    serialized_type_hint: Any = None