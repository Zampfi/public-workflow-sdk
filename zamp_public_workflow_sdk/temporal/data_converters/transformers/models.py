from pydantic import BaseModel
from typing import Any
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn

class GenericSerializedValue(BaseModel):
    serialized_value: Any
    serialized_type_hint: str
    serialized_individual_type_hints: list[str] | None = None
