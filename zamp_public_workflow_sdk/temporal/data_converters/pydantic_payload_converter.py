from pydantic import BaseModel
from temporalio.api.common.v1 import Payload
from temporalio.converter import CompositePayloadConverter, JSONPlainPayloadConverter, AdvancedJSONEncoder, JSONTypeConverter, DefaultPayloadConverter
from typing import Any, List, Type, Optional
import json
from pydantic.json import pydantic_encoder
import base64
from pathlib import Path
import os
import importlib

def get_fqn(cls):
    if cls.__module__ == "builtins":
        return cls.__name__

    return f"{cls.__module__}.{cls.__name__}"

def get_reference_from_fqn(fqn: str):
    module_name, class_name = fqn.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

def custom_pydantic_encoder(o):
    if isinstance(o, bytes):
        return base64.b64encode(o).decode("ascii")

    if isinstance(o, type) and issubclass(o, BaseModel):
        return get_fqn(o)
    
    return pydantic_encoder(o)

class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """

    def to_payload(self, value: Any) -> Optional[Payload]:
        """
        Convert all values with Pydantic encoder or fail.

        Like the base class, we fail if we cannot convert. This payload
        converter is expected to be the last in the chain, so it can fail if
        unable to convert.
        """
        # We let JSON conversion errors be thrown to caller
        return Payload(
            metadata={"encoding": self.encoding.encode()},
            data=json.dumps(
                value, separators=(",", ":"), sort_keys=True, default=custom_pydantic_encoder
            ).encode(),
        )

    def from_payload(self, payload: Payload, type_hint: Type | None = None) -> Any:
        obj = json.loads(payload.data.decode("utf-8"))        
        # If we're expecting a Pydantic model, decode bytes fields automatically
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            for name, field in type_hint.model_fields.items():
                if field.annotation is Type[BaseModel] and name in obj and isinstance(obj[name], str):
                    obj[name] = get_reference_from_fqn(obj[name])

                if field.annotation is bytes and name in obj and isinstance(obj[name], str):
                    try:
                        obj[name] = base64.b64decode(obj[name])
                    except Exception:
                        # If decoding fails, leave the value as is.
                        pass

                if isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
                    if name in obj and isinstance(obj[name], dict):
                        obj[name] = field.annotation.model_validate(obj[name])

            return type_hint.model_validate(obj)

        return obj
    
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
