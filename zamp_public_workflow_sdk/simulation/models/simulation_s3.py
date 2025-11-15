"""S3 models for simulation storage."""

from pydantic import BaseModel, Field


class DownloadFromS3Input(BaseModel):
    """Input model for downloading files from S3."""
    
    bucket_name: str = Field(..., description="Name of the S3 bucket to download from")
    file_name: str = Field(..., description="Name of the file to download")


class UploadToS3Input(BaseModel):
    """Input model for uploading files to S3."""
    
    bucket_name: str = Field(..., description="Name of the S3 bucket to upload to")
    file_name: str = Field(..., description="Name to give the uploaded file")
    blob_base64: str = Field(..., description="File content as base64 encoded string")
    content_type: str = Field(
        default="application/octet-stream", description="Content type of the file"
    )

