from typing import Any

from pydantic import BaseModel


class GenericSerializedValue(BaseModel):
    serialized_value: Any
    serialized_type_hint: str
    serialized_individual_type_hints: list[str] | None = None
