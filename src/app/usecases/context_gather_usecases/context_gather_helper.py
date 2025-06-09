import subprocess

from fastapi import Depends, HTTPException, status
import os
from src.app.services.path_validation_service import PathValidationService
from src.app.services.merkle_tree_service import MerkleTreeService
from src.app.services.code_chunking_service import CodeChunkingService
from src.app.services.file_storage_service import FileStorageService
from src.app.config.database import mongodb_database

class ContextGatherHelper:
    def __init__(self,
                path_validation_service: PathValidationService = Depends(PathValidationService),
                merkle_tree_service: MerkleTreeService = Depends(MerkleTreeService),
                code_chunking_service: CodeChunkingService = Depends(CodeChunkingService),
                file_storage_service: FileStorageService = Depends(FileStorageService),
            ):
        self.path_validation_service = path_validation_service
        self.merkle_tree_service = merkle_tree_service
        self.code_chunking_service = code_chunking_service
        self.file_storage_service = file_storage_service
        self.mongodb = mongodb_database

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
            git_branch_name = result.stdout.decode("utf-8").strip()
            if git_branch_name is None:
                return "default"
            return git_branch_name
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode("utf-8").strip()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get current branch name: {error_message}"
            )
        
    async def chunking_and_storage(self, codebase_path: str, git_branch_name: str):
        """
        Chunk the codebase and store the chunks in the database
        """
        # Create storage key for the merkle tree
        storage_key = f"{git_branch_name}:{codebase_path}"
        print
        
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