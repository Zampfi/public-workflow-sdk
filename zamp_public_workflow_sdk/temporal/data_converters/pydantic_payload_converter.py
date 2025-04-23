import json
from pydantic_core import from_json
from temporalio.api.common.v1 import Payload
from temporalio.converter import CompositePayloadConverter, JSONPlainPayloadConverter, DefaultPayloadConverter
from typing import Any, Type, Optional
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.list_transformer import ListTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytes_transformer import BytesTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytesio_transformer import BytesIOTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_model_metaclass_transformer import PydanticModelMetaclassTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_transformer import PydanticTypeTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.tuple_transformer import TupleTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.datetime_transformer import DateTransformer
from zamp_public_workflow_sdk.temporal.codec.large_payload_codec import CODEC_SENSITIVE_METADATA_KEY, CODEC_SENSITIVE_METADATA_VALUE
from zamp_public_workflow_sdk.temporal.codec.models import CodecModel

class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """
        
    def to_payload(self, value: Any) -> Optional[Payload]:
        metadata = {"encoding": "raw_pydantic_object"}
        if isinstance(value, CodecModel):
            value = value.value
            metadata[CODEC_SENSITIVE_METADATA_KEY] = CODEC_SENSITIVE_METADATA_VALUE.encode()

        return Payload(
            metadata=metadata,
            data=value,
        )

    def from_payload(self, payload: Payload, type_hint: Type | None = None) -> Any:
        return payload.data
    
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