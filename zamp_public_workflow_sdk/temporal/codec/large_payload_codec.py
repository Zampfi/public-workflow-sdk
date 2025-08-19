from temporalio.converter import PayloadCodec
from temporalio.api.common.v1 import Payload
from typing import Iterable, List, Optional
from uuid import uuid4
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from zamp_public_workflow_sdk.temporal.codec.models import BucketData
from zamp_public_workflow_sdk.temporal.codec.storage_client import StorageClient

PAYLOAD_SIZE_THRESHOLD = 100 * 1024
CODEC_BUCKET_ENCODING = "codec_bucket"
CODEC_ENCRYPTED_ENCODING = "codec_encrypted"
CODEC_SENSITIVE_METADATA_KEY = "codec"
CODEC_SENSITIVE_METADATA_VALUE = "sensitive"

class LargePayloadCodec(PayloadCodec):
    def __init__(self, storage_client: StorageClient, encryption_key: Optional[str] = None):
        self.storage_client = storage_client
        self.encryption_key = encryption_key
        if encryption_key is not None:
            self._validate_encryption_key(encryption_key)
            self.cipher = Fernet(encryption_key.encode())

    def _validate_encryption_key(self, encryption_key: str) -> None:
        """
        Validate that the encryption key is in the correct Fernet format.
        Fernet keys are base64-encoded 32-byte keys (44 characters when encoded)
        """        
        try:
            key_bytes = base64.urlsafe_b64decode(encryption_key + '==')
            # Check if the decoded key is exactly 32 bytes
            if len(key_bytes) != 32:
                raise ValueError(f"Encryption key must decode to exactly 32 bytes, got {len(key_bytes)} bytes")
        except Exception as e:
            if isinstance(e, ValueError) and "32 bytes" in str(e):
                raise e
            raise ValueError(f"Invalid encryption key format: {str(e)}")

    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt the payload data using Fernet symmetric encryption."""
        if not self.encryption_key:
            return data
        return self.cipher.encrypt(data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt the payload data using Fernet symmetric encryption."""
        if not self.encryption_key:
            return encrypted_data
        return self.cipher.decrypt(encrypted_data)

    async def encode(self, payload: Iterable[Payload]) -> List[Payload]:
        encoded_payloads = []
        for p in payload:
            if p.ByteSize() > PAYLOAD_SIZE_THRESHOLD or p.metadata.get(CODEC_SENSITIVE_METADATA_KEY, "None".encode()) == CODEC_SENSITIVE_METADATA_VALUE.encode():
                blob_name = f"{uuid4()}"
                await self.storage_client.upload_file(blob_name, p.data)
                bucket_data = BucketData(blob_name, p.metadata.get("encoding", "binary/plain").decode())
                metadata = p.metadata if p.metadata else {}
                metadata["encoding"] = CODEC_BUCKET_ENCODING.encode()
                encoded_payloads.append(Payload(data=bucket_data.get_bytes(), metadata=metadata))
            elif self.encryption_key is not None:
                # Encrypt the data for smaller payloads
                encrypted_data = self._encrypt_data(p.data)
                base64_encrypted_data = base64.b64encode(encrypted_data).decode()
                original_encoding = p.metadata.get("encoding", "binary/plain").decode()
                data_bytes = json.dumps({"data": base64_encrypted_data, "encoding": original_encoding}).encode()
                metadata = p.metadata if p.metadata else {}
                metadata["encoding"] = CODEC_ENCRYPTED_ENCODING.encode()
                encoded_payloads.append(Payload(data=data_bytes, metadata=metadata))
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
                metadata = p.metadata if p.metadata else {}
                metadata["encoding"] = original_encoding.encode()
                decoded_payloads.append(Payload(data=data, metadata=metadata))
            elif encoding == CODEC_ENCRYPTED_ENCODING:
                # Decrypt the data
                data_bytes = json.loads(p.data.decode())
                base64_encrypted_data = data_bytes["data"]
                encrypted_data_bytes = base64.b64decode(base64_encrypted_data)
                data = self._decrypt_data(encrypted_data_bytes)
                original_encoding = data_bytes["encoding"]
                metadata = p.metadata if p.metadata else {}
                metadata["encoding"] = original_encoding.encode()
                decoded_payloads.append(Payload(data=data, metadata=metadata))
            else:
                decoded_payloads.append(p)
        return decoded_payloads

    