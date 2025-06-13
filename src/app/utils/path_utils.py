import os
from typing import List


def get_relative_path(absolute_path: str, codebase_path: str) -> str:
    """
    Convert an absolute path to a relative path based on a codebase path.

    Args:
        absolute_path: The absolute path to convert
        codebase_path: The base codebase path

    Returns:
        Relative path from the codebase path

    Example:
        absolute_path = "/path/to/your/project/src/services/service.js"
        codebase_path = "/path/to/your/project"
        result = "src/services/service.js"
    """
    try:
        # Normalize paths to handle any path separator issues
        abs_path = os.path.normpath(absolute_path)
        base_path = os.path.normpath(codebase_path)

        # Compute relative path
        rel_path = os.path.relpath(abs_path, base_path)

        # If it starts with '..' it means the absolute path is not within the codebase path
        if rel_path.startswith(".."):
            raise ValueError(
                f"The absolute path '{absolute_path}' is not within the codebase path '{codebase_path}'"
            )

        return rel_path
    except Exception as e:
        raise ValueError(
            f"Error converting absolute path to relative path: {str(e)}"
        )


def get_relative_paths(
    absolute_paths: List[str], codebase_path: str
) -> List[str]:
    """
    Convert a list of absolute paths to relative paths based on a codebase path.

    Args:
        absolute_paths: List of absolute paths to convert
        codebase_path: The base codebase path

    Returns:
        List of relative paths from the codebase path
    """
    return [
        get_relative_path(abs_path, codebase_path)
        for abs_path in absolute_paths
    ]


def get_absolute_path(relative_path: str, codebase_path: str) -> str:
    """
    Convert a relative path to an absolute path based on a codebase path.

    Args:
        relative_path: The relative path to convert
        codebase_path: The base codebase path

    Returns:
        Absolute path from the codebase path
    """
    try:
        # Normalize paths to handle any path separator issues
        rel_path = os.path.normpath(relative_path)
        base_path = os.path.normpath(codebase_path)

        # Join paths to get absolute path
        abs_path = os.path.join(base_path, rel_path)

        # Normalize the result to handle any '..' in the path
        abs_path = os.path.normpath(abs_path)

        # Verify the absolute path is within the codebase path
        if not abs_path.startswith(base_path):
            raise ValueError(
                f"The resulting absolute path '{abs_path}' is not within the codebase path '{base_path}'"
            )

        return abs_path
    except Exception as e:
        raise ValueError(
            f"Error converting relative path to absolute path: {str(e)}"
        )
