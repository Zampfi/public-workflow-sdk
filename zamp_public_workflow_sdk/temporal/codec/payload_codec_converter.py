from typing import Sequence, List, Any, Optional
from temporalio.api.common.v1 import Payload
from typing import Type

from zamp_public_workflow_sdk.temporal.data_converters.pydantic_payload_converter import PydanticPayloadConverter
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_model_metaclass_transformer import PydanticModelMetaclassTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_transformer import PydanticTypeTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytes_transformer import BytesTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytesio_transformer import BytesIOTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.datetime_transformer import DateTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.tuple_transformer import TupleTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.collections.list_transformer import ListTransformer


class PayloadCodecConverter:
    def __init__(self):
        pass

    def decode_type_hints(self, payloads: Sequence[Payload], type_hints: Optional[List[Type]] = None) -> List[Any]:
        return None
    
class PydanticPayloadCodecConverter(PayloadCodecConverter):
    def __init__(self):
        super().__init__()
        Transformer.register_transformer(PydanticTypeTransformer())
        Transformer.register_transformer(PydanticModelMetaclassTransformer())
        Transformer.register_transformer(BytesTransformer())
        Transformer.register_transformer(BytesIOTransformer())
        Transformer.register_transformer(DateTransformer())

        Transformer.register_collection_transformer(TupleTransformer())
        Transformer.register_collection_transformer(ListTransformer())

    def decode_type_hints(self, payloads: Sequence[Payload], type_hints: Optional[List[Type]] = None) -> List[Any]:
        
        