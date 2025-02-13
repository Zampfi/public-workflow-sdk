from temporalio.converter import PayloadCodec
from temporalio.api.common.v1 import Payload
from typing import Iterable, List
from google.cloud import storage
from uuid import uuid4

PAYLOAD_SIZE_THRESHOLD = 2 * 1024 * 1024
BUCKET_NAME = "temporal-large-payloads"

class LargePayloadCodec(PayloadCodec):
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(BUCKET_NAME)

    async def encode(self, payload: Iterable[Payload]) -> List[Payload]:
        encoded_payloads = []
        for p in payload:
            if p.ByteSize() > PAYLOAD_SIZE_THRESHOLD:
                blob = self.bucket.blob(f"{uuid4()}")
                blob.upload_from_string(p.data)
                encoded_payloads.append(Payload(data=blob.public_url, metadata={"encoding": "gcs"}))
            else:
                encoded_payloads.append(p)

        return encoded_payloads

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        decoded_payloads = []
        for p in payloads:
            if p.metadata.get("encoding") == "gcs":
                blob = self.bucket.blob(p.data)
                decoded_payloads.append(Payload(data=blob.download_as_bytes()))
            else:
                decoded_payloads.append(p)
        return decoded_payloads