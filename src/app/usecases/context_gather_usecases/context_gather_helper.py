import subprocess

from fastapi import Depends, HTTPException, status

from src.app.services.path_validation_service import PathValidationService


class ContextGatherHelper:
    def __init__(self, path_validation_service: PathValidationService = Depends(PathValidationService)):
        self.path_validation_service = path_validation_service

    async def get_current_branch_name(self, codebase_path: str) -> str | None:
        """
        Get the current branch name of the git repository at the given codebase path.
        
        Returns:
            str | None: Branch name if git repository exists, None otherwise
        """
        # Validate if the path exists and is accessible
        self.path_validation_service.validate_codebase_path(codebase_path)
        
        # Check if it's a git repository
        if not self.path_validation_service.validate_git_repository(codebase_path):
            return None

        try:
            result = subprocess.run(
                ["git", "-C", codebase_path, "rev-parse", "--abbrev-ref", "HEAD"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return result.stdout.decode("utf-8").strip()
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode("utf-8").strip()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get current branch name: {error_message}"
            )