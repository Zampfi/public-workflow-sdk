from temporalio.converter import DataConverter, PayloadCodec, PayloadConverter, CompositePayloadConverter
import dataclasses
from typing import Type
from temporalio.api.common.v1 import Payload
from typing import Sequence, List, Any, Optional
import temporalio.api.common.v1
from zamp_public_workflow_sdk.temporal.codec.payload_codec_converter import PayloadCodecConverter, PydanticPayloadCodecConverter

class PydanticCodecDataConverter(DataConverter):
    def __init__(self):
        super().__init__()
        self.pydantic_codec_converter: PayloadCodecConverter = PydanticPayloadCodecConverter()

    async def decode(
        self,
        payloads: Sequence[temporalio.api.common.v1.Payload],
        type_hints: Optional[List[Type]] = None,
    ) -> List[Any]:
        
        if self.pydantic_codec_converter :
            payloads = await self.pydantic_codec_converter.decode_type_hints(payloads, type_hints)

        return super().decode(payloads, type_hints)

    @staticmethod
    def default() -> 'PydanticCodecDataConverter':
        return PydanticCodecDataConverter()

class BaseDataConverter:
    def __init__(self, converter: DataConverter = DataConverter.default):
        self.converter = converter

    def replace_payload_codec(self, payload_codec: PayloadCodec) -> 'BaseDataConverter':
        self.converter = dataclasses.replace(self.converter, payload_codec=payload_codec)
        return self
    
    def replace_payload_converter(self, payload_converter_type: Type[PayloadConverter]) -> 'BaseDataConverter':
        self.converter = dataclasses.replace(self.converter, payload_converter_class=payload_converter_type)
        return self
        
    def get_converter(self) -> DataConverter:
        return self.converter