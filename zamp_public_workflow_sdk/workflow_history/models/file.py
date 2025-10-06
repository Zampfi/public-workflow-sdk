from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field


class FileProvider(str, Enum):
    S3 = "s3"
    GCP = "gcp"


class FileMetadata(BaseModel):
    path: str
    bucket: str


class S3FileMetadata(FileMetadata):
    provider: Literal["s3"] = "s3"


class GCPFileMetadata(FileMetadata):
    provider: Literal["gcp"] = "gcp"


class File(BaseModel):
    id: str = Field(description="The unique identifier for the file")
    provider: FileProvider = Field(description="The provider of the file")
    metadata: Union[S3FileMetadata, GCPFileMetadata] = Field(
        description="The metadata for the file", discriminator="provider"
    )

    def get_file_name(self) -> str:
        if not self.metadata.path:
            raise ValueError("File metadata path is required")
        return self.metadata.path.split("/")[-1]
