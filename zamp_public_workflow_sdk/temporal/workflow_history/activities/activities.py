"""
Activities for temporal workflow history operations.
"""

from typing import Any
import structlog
from temporalio import activity
from pydantic import BaseModel, Field
from zamp_public_workflow_sdk.temporal.workflow_history.constants.constants import PayloadField

logger = structlog.get_logger(__name__)


class DecodeNodePayloadInput(BaseModel):
    """Input model for decode_node_payload activity."""
    
    node_id: str = Field(..., description="The node ID")
    encoded_payload: dict[str, Any] = Field(..., description="The encoded payload to decode")


@activity.defn(name="decode_node_payload")
async def decode_node_payload(input_data: DecodeNodePayloadInput) -> Any:
    """
    Activity to decode encoded node payloads using TemporalWorkflowHistoryService.

    Args:
        input_data: The input data containing node_id and encoded_payload

    Returns:
        The decoded payload data value (extracted from the decoded payload object)
    """
    logger.info("Decoding node payload", node_id=input_data.node_id)
    
    try:
        # Import here to avoid circular imports
        from pantheon_v2.platform.temporal.workflow_history.services.temporal_workflow_history_service import (
            TemporalWorkflowHistoryService,
        )
        
        # Create service instance
        service = TemporalWorkflowHistoryService()
        
        decoded_payloads = await service._decode_payloads([input_data.encoded_payload], service._codec)
        
        if decoded_payloads and len(decoded_payloads) > 0:
            decoded_payload_obj = decoded_payloads[0]
            if isinstance(decoded_payload_obj, dict) and PayloadField.DATA.value in decoded_payload_obj:
                decoded_result = decoded_payload_obj[PayloadField.DATA.value]
                logger.info("Successfully decoded node payload", node_id=input_data.node_id)
                return decoded_result
            else:
                logger.warning("Decoded payload doesn't have expected structure", node_id=input_data.node_id)
                return decoded_payload_obj
        else:
            logger.warning("No decoded payload returned", node_id=input_data.node_id)
            return input_data.encoded_payload.get("data", None)
            
    except Exception as e:
        logger.error(
            "Failed to decode node payload",
            node_id=input_data.node_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        # Return the raw data if decoding fails
        return input_data.encoded_payload.get("data", None)
