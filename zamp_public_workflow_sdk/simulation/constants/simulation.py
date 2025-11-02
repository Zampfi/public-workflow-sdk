"""Constants for simulation module."""

from enum import Enum


class PayloadKey(str, Enum):
    """Keys for accessing input/output payloads."""

    INPUT_PAYLOAD = "input_payload"
    OUTPUT_PAYLOAD = "output_payload"


# Metadata flag indicating child workflow needs to be fetched for its output
NEEDS_CHILD_TRAVERSAL = "needs_child_traversal"

# Keys for decoded payload data
DECODED_INPUT = "decoded_input"
DECODED_OUTPUT = "decoded_output"
