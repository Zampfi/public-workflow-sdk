from temporalio.converter import PayloadCodec, DataConverter
from temporalio.api.common.v1 import Payload
from typing import Iterable, List
from uuid import uuid4
import json
from zamp_public_workflow_sdk.temporal.codec.models import BucketData
from zamp_public_workflow_sdk.temporal.codec.storage_client import StorageClient

from zamp_public_workflow_sdk.temporal.data_converters.context_manager import DataConverterContextManager

PAYLOAD_SIZE_THRESHOLD = 100 * 1024
CODEC_BUCKET_ENCODING = "codec_bucket"
CODEC_SENSITIVE_METADATA_KEY = "codec"
CODEC_SENSITIVE_METADATA_VALUE = "sensitive"

class LargePayloadCodec(PayloadCodec):
    def __init__(self, storage_client: StorageClient):
        self.storage_client = storage_client

    async def encode(self, payload: Iterable[Payload]) -> List[Payload]:
        byte_size = 0
        with DataConverterContextManager("LargePayloadCodec.Encode") as context_manager:
            encoded_payloads = []
            for p in payload:
                payload_byte_size = p.ByteSize()
                byte_size += payload_byte_size
                if payload_byte_size > PAYLOAD_SIZE_THRESHOLD or p.metadata.get(CODEC_SENSITIVE_METADATA_KEY, "None".encode()) == CODEC_SENSITIVE_METADATA_VALUE.encode():
                    blob_name = f"{uuid4()}"
                    await self.storage_client.upload_file(blob_name, p.data)
                    bucket_data = BucketData(blob_name, p.metadata.get("encoding", "binary/plain").decode())
                    encoded_payloads.append(Payload(data=bucket_data.get_bytes(), metadata={"encoding": CODEC_BUCKET_ENCODING.encode()}))
                else:
                    encoded_payloads.append(p)
                    
            context_manager.set_data_length(byte_size)

        return encoded_payloads

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        decoded_payloads = []
        byte_size = 0
        with DataConverterContextManager("LargePayloadCodec.Decode") as context_manager:
            for p in payloads:
                encoding = p.metadata.get("encoding", "binary/plain").decode()
                if encoding == CODEC_BUCKET_ENCODING:
                    bucket_metadata = json.loads(p.data.decode())
                    blob_name = bucket_metadata["data"]
                    original_encoding = bucket_metadata["encoding"]
                    data = await self.storage_client.get_file(blob_name)
                    byte_size += len(data)
                    decoded_payloads.append(Payload(data=data, metadata={"encoding": original_encoding.encode()}))
                else:
                    decoded_payloads.append(p)
                
            context_manager.set_data_length(byte_size)

        return decoded_payloads

    