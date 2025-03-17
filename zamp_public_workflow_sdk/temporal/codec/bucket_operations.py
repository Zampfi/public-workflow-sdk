from abc import ABC, abstractmethod
from google.cloud import storage

class StorageClient(ABC):
    @abstractmethod
    def upload_file(self, object_name: str, data: bytes | str) -> None:
        pass

    @abstractmethod
    def get_file(self, object_name: str) -> bytes:
        pass

class GCSClient(StorageClient):
    def __init__(self, project_id: str, bucket_name: str):
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(self, object_name: str, data: bytes | str) -> None:
        self.bucket.blob(object_name).upload_from_string(data)

    def get_file(self, object_name: str) -> bytes:
        return self.bucket.blob(object_name).download_as_bytes()