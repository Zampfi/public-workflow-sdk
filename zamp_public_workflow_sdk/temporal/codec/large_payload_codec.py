from temporalio.converter import PayloadCodec, DataConverter
from temporalio.api.common.v1 import Payload
from typing import Iterable, List
from google.cloud import storage
from uuid import uuid4
import json

PAYLOAD_SIZE_THRESHOLD = 2 * 1024 * 1024

class GcsData:
    def __init__(self, data: str, encoding: str):
        self.data = data
        self.encoding = encoding

    def get_bytes(self) -> bytes:
        return json.dumps({"data": self.data, "encoding": self.encoding}).encode()

class LargePayloadCodec(PayloadCodec):
    def __init__(self, project_id: str, bucket_name: str):
        self.storage_client = storage.Client(project=project_id)
        self.bucket_name = bucket_name

    async def encode(self, payload: Iterable[Payload]) -> List[Payload]:
        encoded_payloads = []
        bucket = self.storage_client.get_bucket(self.bucket_name)
        for p in payload:
            if p.ByteSize() > PAYLOAD_SIZE_THRESHOLD:
                blob_name = f"{uuid4()}"
                blob = bucket.blob(blob_name)
                blob.upload_from_string(p.data)
                gcs_data = GcsData(blob_name, p.metadata.get("encoding", "binary/plain").decode())
                encoded_payloads.append(Payload(data=gcs_data.get_bytes(), metadata={"encoding": "gcs".encode()}))
            else:
                encoded_payloads.append(p)

        return encoded_payloads

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        decoded_payloads = []
        bucket = self.storage_client.get_bucket(self.bucket_name)
        for p in payloads:
            encoding = p.metadata.get("encoding", "binary/plain").decode()
            if encoding == "gcs":
                # Decode the payload data from the GCS URL
                gcs_data = json.loads(p.data.decode())
                blob_name = gcs_data["data"]
                original_encoding = gcs_data["encoding"]

                blob = bucket.blob(blob_name)
                decoded_payloads.append(Payload(data=blob.download_as_bytes(), metadata={"encoding": original_encoding.encode()}))
            else:
                decoded_payloads.append(p)
                
        return decoded_payloads

    