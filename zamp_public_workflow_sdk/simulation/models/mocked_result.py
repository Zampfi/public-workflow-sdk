from typing import Any
from pydantic import BaseModel, Field, RootModel


class MockedResultInput(BaseModel):
    """Input model for return_mocked_result activity.

    Contains separate input and output payloads that may or may not be encoded.
    """

    node_id: str = Field(..., description="The node execution ID")
    input_payload: Any = Field(
        default=None,
        description="Input payload data (may be encoded or raw)",
    )
    output_payload: Any = Field(
        default=None,
        description="Output payload data (may be encoded or raw)",
    )
    action_name: str | None = Field(default=None, description="Optional action name for activity summary")


class MockedResultOutput(RootModel[Any]):
    """Output model for return_mocked_result activity.

    Contains the decoded output payload value, which can be any JSON-serializable type.
    """

    root: Any
