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
import time
from temporalio import workflow
from zamp_public_workflow_sdk.temporal.data_converters.context_manager import DataConverterContextManager

import structlog
logger = structlog.get_logger(__name__)

class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """
    def __init__(self):
        super().__init__()
        Transformer.register_transformer(PydanticTypeTransformer())
        Transformer.register_transformer(PydanticModelMetaclassTransformer())
        Transformer.register_transformer(BytesTransformer())
        Transformer.register_transformer(BytesIOTransformer())
        Transformer.register_transformer(DateTransformer())
        Transformer.register_transformer(UnionTransformer())

        Transformer.register_collection_transformer(TupleTransformer())
        Transformer.register_collection_transformer(ListTransformer())
        
    def to_payload(self, value: Any) -> Optional[Payload]:
        # Use sandbox_unrestricted to move serialization outside the sandbox
        with workflow.unsafe.sandbox_unrestricted():
            metadata = {"encoding": self.encoding.encode()}
            if isinstance(value, CodecModel):
                value = value.value
                metadata[CODEC_SENSITIVE_METADATA_KEY] = CODEC_SENSITIVE_METADATA_VALUE.encode()

            with DataConverterContextManager("PydanticJSONPayloadConverter.Serialize") as context_manager:
                json_data = json.dumps(value, separators=(",", ":"), sort_keys=True, default=lambda x: Transformer.serialize(x).serialized_value)
                data = json_data.encode()
                context_manager.set_data_length(len(data))
                return Payload(
                    metadata=metadata,
                    data=data,
                )

    def from_payload(self, payload: Payload, type_hint: Type | None = None) -> Any:
        # Use sandbox_unrestricted to move deserialization outside the sandbox
        with workflow.unsafe.sandbox_unrestricted():
            with DataConverterContextManager("PydanticJSONPayloadConverter.Deserialize", len(payload.data)):
                obj = from_json(payload.data)
                deserialized = Transformer.deserialize(obj, type_hint)
                return deserialized
    
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