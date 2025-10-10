"""
Common decorators for ActionsHub - independent of Pantheon platform.
"""

from typing import TypeVar

T = TypeVar("T")


def external(something: T) -> T:
    """Mark a class or function as external to the platform."""
    setattr(something, "_is_external", True)
    return something
