"""Version constants for simulation configuration."""

from enum import Enum


class SupportedVersions(str, Enum):
    """Supported simulation configuration versions."""

    V1_0_0 = "1.0.0"
