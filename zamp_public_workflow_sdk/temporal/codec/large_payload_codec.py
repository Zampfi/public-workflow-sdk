from temporalio.converter import PayloadCodec, DataConverter
from temporalio.api.common.v1 import Payload
from typing import Iterable, List
from uuid import uuid4
import json
from zamp_public_workflow_sdk.temporal.codec.models import BucketData
from zamp_public_workflow_sdk.temporal.codec.storage_client import StorageClient

PAYLOAD_SIZE_THRESHOLD = 2 * 1024 * 1024
CODEC_BUCKET_ENCODING = "codec_bucket"
CODEC_SENSITIVE_METADATA_KEY = "codec"
CODEC_SENSITIVE_METADATA_VALUE = "sensitive"

class LargePayloadCodec(PayloadCodec):
    def __init__(self, storage_client: StorageClient):
        self.storage_client = storage_client

    async def encode(self, payload: Iterable[Payload]) -> List[Payload]:
        encoded_payloads = []
        for p in payload:
            if p.ByteSize() > PAYLOAD_SIZE_THRESHOLD or p.metadata.get(CODEC_SENSITIVE_METADATA_KEY, "None".encode()) == CODEC_SENSITIVE_METADATA_VALUE.encode():
                blob_name = f"{uuid4()}"
                await self.storage_client.upload_file(blob_name, p.data)
                bucket_data = BucketData(blob_name, p.metadata.get("encoding", "binary/plain").decode())
                encoded_payloads.append(Payload(data=bucket_data.get_bytes(), metadata={"encoding": CODEC_BUCKET_ENCODING.encode()}))
            else:
                encoded_payloads.append(p)

        return encoded_payloads

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        decoded_payloads = []
        for p in payloads:
            encoding = p.metadata.get("encoding", "binary/plain").decode()
            if encoding == CODEC_BUCKET_ENCODING:
                bucket_metadata = json.loads(p.data.decode())
                blob_name = bucket_metadata["data"]
                original_encoding = bucket_metadata["encoding"]
                data = await self.storage_client.get_file(blob_name)
                decoded_payloads.append(Payload(data=data, metadata={"encoding": original_encoding.encode()}))
            else:
                decoded_payloads.append(p)
                
        return decoded_payloads

    