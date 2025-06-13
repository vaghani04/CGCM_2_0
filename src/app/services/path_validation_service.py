import os
from pathlib import Path

from fastapi import HTTPException, status


class PathValidationService:
    def __init__(self):
        pass

    def validate_codebase_path(self, codebase_path: str) -> None:
        """
        Validate if the provided codebase path exists and is accessible.

        Args:
            codebase_path: The path to validate

        Raises:
            HTTPException: 400 if path doesn't exist or is not accessible
        """
        if not codebase_path or not codebase_path.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Codebase path cannot be empty",
            )

        path = Path(codebase_path).resolve()

        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No such file or directory: '{codebase_path}'",
            )

        if not path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path '{codebase_path}' is not a directory",
            )

        if not os.access(path, os.R_OK):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Directory '{codebase_path}' is not readable",
            )

    def validate_git_repository(self, codebase_path: str) -> bool:
        """
        Validate if the provided path contains a git repository.

        Args:
            codebase_path: The path to check for git repository

        Returns:
            bool: True if valid git repository exists, False otherwise
        """
        path = Path(codebase_path).resolve()
        git_dir = path / ".git"

        if not git_dir.exists():
            return False

        if not git_dir.is_dir():
            return False

        return True
