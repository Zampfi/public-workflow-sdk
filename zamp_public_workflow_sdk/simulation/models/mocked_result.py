from typing import Any
from pydantic import BaseModel


class MockedResultInput(BaseModel):
    """Input model for return_mocked_result activity."""

    node_id: str
    output: Any
