import os
import hashlib
from typing import Dict, List, Any
from fastapi import Depends, HTTPException

from src.app.usecases.context_gather_usecases.context_gather_helper import ContextGatherHelper
from src.app.services.merkle_tree_service import MerkleTreeService
from src.app.services.code_chunking_service import CodeChunkingService
from src.app.services.file_storage_service import FileStorageService
from src.app.config.database import mongodb_database

class ContextGatherUseCase:
    def __init__(
        self,
        context_gather_helper: ContextGatherHelper = Depends(ContextGatherHelper),
        merkle_tree_service: MerkleTreeService = Depends(MerkleTreeService),
        code_chunking_service: CodeChunkingService = Depends(CodeChunkingService),
        file_storage_service: FileStorageService = Depends(FileStorageService),
    ):
        self.context_gather_helper = context_gather_helper
        self.merkle_tree_service = merkle_tree_service
        self.code_chunking_service = code_chunking_service
        self.file_storage_service = file_storage_service
        self.mongodb = mongodb_database
        
    async def execute(self, codebase_path: str):
        """
        Execute the context gathering process up to MongoDB storage
        
        Args:
            codebase_path: Path to the codebase
            
        Returns:
            Dictionary with statistics and results
        """
        # Get git branch name
        # git_branch_name = await self.context_gather_helper.get_current_branch_name(codebase_path)

        # stats = await self.context_gather_helper.chunking_and_storage(codebase_path, git_branch_name)

        repo_map = await self.context_gather_helper.generate_repo_map(codebase_path)
        return repo_map