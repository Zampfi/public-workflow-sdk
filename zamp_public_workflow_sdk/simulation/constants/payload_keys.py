"""Constants for payload keys used in simulation."""

from enum import Enum


class PayloadKey(str, Enum):
    """Keys for accessing input/output payloads in simulation data structures."""

    INPUT_PAYLOAD = "input_payload"
    OUTPUT_PAYLOAD = "output_payload"


# Metadata flag indicating child workflow needs to be fetched for its output
NEEDS_CHILD_TRAVERSAL = "needs_child_traversal"
