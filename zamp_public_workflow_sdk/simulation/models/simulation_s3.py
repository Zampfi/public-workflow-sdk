from pydantic import BaseModel, Field
from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig
from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload


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


class GetSimulationDataFromS3Input(BaseModel):
    simulation_s3_key: str = Field(..., description="S3 key where simulation data is stored")
    bucket_name: str = Field(..., description="S3 bucket name where simulation data is stored")


class SimulationMemo(BaseModel):
    config: SimulationConfig = Field(..., description="Simulation configuration")
    node_id_to_payload_map: dict[str, NodePayload] = Field(..., description="Mapping of node IDs to their payloads")


class GetSimulationDataFromS3Output(BaseModel):
    simulation_memo: SimulationMemo = Field(..., description="Simulation memo data loaded from S3")
