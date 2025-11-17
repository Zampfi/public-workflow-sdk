"""Constants for simulation module."""

from enum import Enum


class PayloadKey(str, Enum):
    """Keys for accessing input/output payloads."""

    INPUT_PAYLOAD = "input_payload"
    OUTPUT_PAYLOAD = "output_payload"


# Keys for decoded payload data
DECODED_INPUT = "decoded_input"
DECODED_OUTPUT = "decoded_output"

# Memo key for storing S3 location of simulation data
SIMULATION_S3_KEY_MEMO = "__simulation_s3_key"
# Memo key for storing S3 bucket name for simulation data
SIMULATION_S3_BUCKET_MEMO = "__simulation_s3_bucket"


def get_simulation_s3_key(workflow_id: str) -> str:
    f"""
    Generate the S3 key for simulation data stored in S3.

    Args:
        workflow_id: The workflow ID

    Returns:
        The S3 key in format: {workflow_id}.json"
    """
    return f"{workflow_id}.json"
