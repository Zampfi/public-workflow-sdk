from typing import Any
from pydantic import BaseModel, Field


class MockedResultInput(BaseModel):
    """Input model for return_mocked_result activity.

    The encoded_payload should be a dict with PayloadKey.INPUT_PAYLOAD and PayloadKey.OUTPUT_PAYLOAD keys:
    {
        PayloadKey.INPUT_PAYLOAD: {...},   # encoded input payload
        PayloadKey.OUTPUT_PAYLOAD: {...}   # encoded output payload
    }
    """

    node_id: str = Field(..., description="The node execution ID")
    encoded_payload: dict[str, Any] = Field(
        ...,
        description="Dict with PayloadKey.INPUT_PAYLOAD and PayloadKey.OUTPUT_PAYLOAD keys containing encoded payloads",
    )
    action_name: str | None = Field(default=None, description="Optional action name for activity summary")
