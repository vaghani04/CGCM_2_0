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
        git_branch_name = await self.context_gather_helper.get_current_branch_name(codebase_path)
        
        if not git_branch_name:
            git_branch_name = "default"
            
        # Create storage key for the merkle tree
        storage_key = f"{git_branch_name}:{codebase_path}"
        
        # Initialize statistics
        stats = {
            "git_branch": git_branch_name,
            "workspace_path": codebase_path,
            "total_files_processed": 0,
            "total_chunks_created": 0,
            "total_chunks_reused": 0,
            "changed_files": []
        }
        
        # Build current merkle tree
        current_tree, current_file_hashes = self.merkle_tree_service.build_merkle_tree(codebase_path)
        
        # Check if we have a previous merkle tree
        previous_data = self.file_storage_service.get_merkle_tree(storage_key)
        
        # Files that need processing
        files_to_process = []
        
        if previous_data:
            previous_tree, previous_file_hashes = previous_data
            
            # Compare trees to find changed files
            changed_files = self.merkle_tree_service.compare_merkle_trees(
                previous_tree, current_tree, previous_file_hashes, current_file_hashes
            )
            
            # Only process changed files
            files_to_process = [os.path.join(codebase_path, file_path) for file_path in changed_files]
            stats["changed_files"] = changed_files
        else:
            # Process all files if no previous tree
            files_to_process = [
                os.path.join(codebase_path, file_path) 
                for file_path in current_file_hashes.keys()
            ]
            stats["changed_files"] = list(current_file_hashes.keys())
            
        # Store the current merkle tree
        self.file_storage_service.store_merkle_tree(storage_key, current_tree, current_file_hashes)
        
        stats["total_files_processed"] = len(files_to_process)
        
        # Process files and generate chunks
        all_chunks = []
        for file_path in files_to_process:
            chunks = self.code_chunking_service.chunk_file(file_path, codebase_path, git_branch_name)
            all_chunks.extend(chunks)
            
        stats["total_chunks_created"] = len(all_chunks)
        
        # Store chunks in MongoDB
        if all_chunks:
            # Convert workspace path to a valid database name
            db_name = os.path.basename(codebase_path.rstrip('/'))
            db_name = ''.join(c if c.isalnum() else '_' for c in db_name)
            
            # Get MongoDB client
            mongo_client = self.mongodb.get_mongo_client()
            db = mongo_client[db_name]
            collection = db['chunks']
            
            # Insert chunks using upsert based on chunk_hash
            for chunk in all_chunks:
                await collection.update_one(
                    {'chunk_hash': chunk['chunk_hash']},
                    {'$set': chunk},
                    upsert=True
                )
        
        return stats