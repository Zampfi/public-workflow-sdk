from temporalio.converter import DataConverter, PayloadCodec, PayloadConverter, CompositePayloadConverter
import dataclasses
from typing import Type

class BaseDataConverter:
    converter = DataConverter.default

    def replace_payload_codec(self, payload_codec: PayloadCodec) -> 'BaseDataConverter':
        self.converter = dataclasses.replace(self.converter, payload_codec=payload_codec)
        return self
    
    def replace_payload_converter(self, payload_converter_type: Type[PayloadConverter]) -> 'BaseDataConverter':
        self.converter = dataclasses.replace(self.converter, payload_converter_class=payload_converter_type)
        return self
        
    def get_converter(self) -> DataConverter:
        return self.converter