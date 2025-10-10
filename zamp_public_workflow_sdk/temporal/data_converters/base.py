from __future__ import annotations
import dataclasses

from temporalio.converter import DataConverter, PayloadCodec, PayloadConverter


class BaseDataConverter:
    converter = DataConverter.default

    def replace_payload_codec(self, payload_codec: PayloadCodec) -> BaseDataConverter:
        self.converter = dataclasses.replace(self.converter, payload_codec=payload_codec)
        return self

    def replace_payload_converter(self, payload_converter_type: type[PayloadConverter]) -> BaseDataConverter:
        self.converter = dataclasses.replace(self.converter, payload_converter_class=payload_converter_type)
        return self

    def get_converter(self) -> DataConverter:
        return self.converter
