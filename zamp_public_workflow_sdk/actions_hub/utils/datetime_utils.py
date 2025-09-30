"""
Simplified datetime utilities for ActionsHub - removes complex dependencies.
"""

import pandas as pd


def convert_iso_to_timedelta(iso_string: str) -> pd.Timedelta:
    """
    Convert ISO 8601 duration string to pandas Timedelta.

    Args:
        iso_string: ISO 8601 duration string like "P1DT2H30M15S500MS"

    Returns:
        pd.Timedelta object
    """
    return pd.Timedelta(iso_string)
