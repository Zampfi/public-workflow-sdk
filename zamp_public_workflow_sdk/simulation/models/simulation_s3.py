from pydantic import BaseModel, Field


class DownloadFromS3Input(BaseModel):
    bucket_name: str = Field(..., description="Name of the S3 bucket to download from")
    file_name: str = Field(..., description="Name of the file to download")


class UploadToS3Input(BaseModel):
    bucket_name: str = Field(..., description="Name of the S3 bucket to upload to")
    file_name: str = Field(..., description="Name to give the uploaded file")
    blob_base64: str = Field(..., description="File content as base64 encoded string")
    content_type: str = Field(default="application/octet-stream", description="Content type of the file")

    class Config:
        arbitrary_types_allowed = True


class DownloadFromS3Output(BaseModel):
    content_base64: str = Field(..., description="File content as base64 encoded string")

    class Config:
        arbitrary_types_allowed = True


class UploadToS3Output(BaseModel):
    metadata: dict = Field(..., description="Metadata of the uploaded file")
    s3_url: str = Field(..., description="S3 URL of the uploaded file (s3://...)")
    https_url: str = Field(
        ...,
        description="HTTPS URL of the uploaded file (https://s3.amazonaws.com/...)",
    )
