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
