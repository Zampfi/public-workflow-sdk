import json
from pydantic_core import from_json
from temporalio.api.common.v1 import Payload
from temporalio.converter import CompositePayloadConverter, JSONPlainPayloadConverter, DefaultPayloadConverter
from typing import Any, Type, Optional
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
from zamp_public_workflow_sdk.temporal.data_converters.transformers.tuple_transformer import TupleTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.datetime_transformer import DateTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.any_transformer import AnyTransformer

class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """
    def __init__(self):
        super().__init__()
        Transformer.register_transformer(AnyTransformer())
        Transformer.register_transformer(UnionTransformer())
        Transformer.register_transformer(PydanticTypeTransformer())
        Transformer.register_transformer(PydanticTypeVarTransformer())
        Transformer.register_transformer(PydanticModelMetaclassTransformer())
        Transformer.register_transformer(TupleTransformer())
        Transformer.register_transformer(BytesTransformer())
        Transformer.register_transformer(BytesIOTransformer())
        Transformer.register_transformer(DateTransformer())

        # Keep this in the last position
        Transformer.register_transformer(PydanticTransformer())
        Transformer.register_transformer(ListTransformer())
        Transformer.register_transformer(DictTransformer())
        
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