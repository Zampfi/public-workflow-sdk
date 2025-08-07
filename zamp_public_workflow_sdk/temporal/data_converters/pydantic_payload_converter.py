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
from zamp_public_workflow_sdk.temporal.data_converters.transformers.union_transformer import UnionTransformer
from zamp_public_workflow_sdk.temporal.codec.large_payload_codec import CODEC_SENSITIVE_METADATA_KEY, CODEC_SENSITIVE_METADATA_VALUE
from zamp_public_workflow_sdk.temporal.codec.models import CodecModel
from temporalio import workflow

from temporalio.contrib.pydantic import PydanticJSONPlainPayloadConverter

from zamp_public_workflow_sdk.temporal.data_converters.type_utils import is_serialize_by_default_serializer

import structlog
logger = structlog.get_logger(__name__)

DEFAULT_CONVERTER_METADATA_KEY = "default_converter"

class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """
    def __init__(self):
        super().__init__()
        self.temporal_pydantic_converter = PydanticJSONPlainPayloadConverter()
        
    def to_payload(self, value: Any) -> Optional[Payload]:
        # Use sandbox_unrestricted to move serialization outside the sandbox
        with workflow.unsafe.sandbox_unrestricted():
            metadata = {}
            if isinstance(value, CodecModel):
                value = value.value
                metadata[CODEC_SENSITIVE_METADATA_KEY] = CODEC_SENSITIVE_METADATA_VALUE.encode()

            payload = self.temporal_pydantic_converter.to_payload(value)
            if metadata and len(metadata) > 0:
                payload.metadata.update(metadata)
            return payload

    def from_payload(self, payload: Payload, type_hint: Type | None = None) -> Any:
        # Use sandbox_unrestricted to move deserialization outside the sandbox
        with workflow.unsafe.sandbox_unrestricted():
            return self.temporal_pydantic_converter.from_payload(payload, type_hint)
    
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