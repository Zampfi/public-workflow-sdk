"""
Helper functions for ActionsHub - independent of Pantheon platform.
"""

from typing import Any, List, Dict
from copy import deepcopy


def remove_connection_id(schema: List[Any]) -> List[Any]:
    """Remove connection_id from schema by removing items with title 'ConnectionIdentifier' and type 'object'"""
    if not schema:
        return schema

    result = []
    for arg in schema:
        if (
            isinstance(arg, dict)
            and arg.get("title") == "ConnectionIdentifier"
            and arg.get("type") == "object"
        ):
            # Skip this dictionary item
            continue
        elif isinstance(arg, list):
            # Filter out any ConnectionIdentifier objects from the list
            filtered_list = [
                item
                for item in arg
                if not (
                    isinstance(item, dict)
                    and item.get("title") == "ConnectionIdentifier"
                    and item.get("type") == "object"
                )
            ]
            if filtered_list:  # Only add non-empty lists
                result.append(filtered_list)
        else:
            result.append(arg)
    return result


def find_connection_id_path(schema: List[Any]) -> List[str]:
    """Find the path to connection_id by finding object with title 'ConnectionIdentifier' and type 'object'"""
    if not schema:
        return ["connection_id"]

    # Check each item in the schema for ConnectionIdentifier
    for i, item in enumerate(schema):
        if (
            isinstance(item, dict)
            and item.get("title") == "ConnectionIdentifier"
            and item.get("type") == "object"
        ):
            return [str(i), "connection_id"]

        # Check if it's a list that might contain a ConnectionIdentifier
        elif isinstance(item, list):
            for j, sub_item in enumerate(item):
                if (
                    isinstance(sub_item, dict)
                    and sub_item.get("title") == "ConnectionIdentifier"
                    and sub_item.get("type") == "object"
                ):
                    return [str(i), str(j), "connection_id"]

    # Default fallback
    return ["connection_id"]


def inject_connection_id(
    params: Dict[str, Any], connection_id: str, path: List[str]
) -> List[Dict[str, Any]]:
    """
    Insert connection_id at the specified path in params.
    Returns a list with connection_id as the first element and params as the second.

    Args:
        params: The parameters dictionary
        connection_id: The connection ID to inject
        path: The path where to inject the connection ID (typically ['0', 'connection_id'])

    Returns:
        A list with connection_id in the first dictionary and params in the second
    """
    # If path starts with 0, put connection_id in first element (most common case)
    if path and path[0] == "0":
        return [{"connection_id": connection_id}, deepcopy(params)]
    else:
        # This is a fallback for other paths, but the expected format is
        # connection_id in the first element for most cases
        return [deepcopy(params), {"connection_id": connection_id}]
