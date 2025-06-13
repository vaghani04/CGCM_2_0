import asyncio
import json
import os
import subprocess

from fastapi import Depends, HTTPException, status

from src.app.config.database import mongodb_database
from src.app.services.code_chunking_service import CodeChunkingService
from src.app.services.file_storage_service import FileStorageService
from src.app.services.merkle_tree_service import MerkleTreeService
from src.app.services.path_validation_service import PathValidationService
from src.app.services.repo_map_service import RepositoryMapService
from src.app.usecases.context_gather_usecases.codebase_indexing_usecase import (
    CodebaseIndexingUseCase,
)
from src.app.usecases.context_gather_usecases.extract_nl_context_usecase import (
    ExtractNLContextUseCase,
)
from src.app.usecases.context_gather_usecases.repo_map_graphdb_usecase import (
    RepoMapGraphDBUseCase,
)
from src.app.utils.hash_calculator import calculate_hash
from src.app.utils.logging_util import loggers
from src.app.utils.path_utils import get_relative_paths
from src.app.utils.tracing_context_utils import context_variable_git_branch_name


class ContextGatherHelper:
    def __init__(
        self,
        path_validation_service: PathValidationService = Depends(
            PathValidationService
        ),
        merkle_tree_service: MerkleTreeService = Depends(MerkleTreeService),
        code_chunking_service: CodeChunkingService = Depends(
            CodeChunkingService
        ),
        file_storage_service: FileStorageService = Depends(FileStorageService),
        codebase_indexing_use_case: CodebaseIndexingUseCase = Depends(
            CodebaseIndexingUseCase
        ),
        repo_map_service: RepositoryMapService = Depends(RepositoryMapService),
        extract_nl_context_use_case: ExtractNLContextUseCase = Depends(
            ExtractNLContextUseCase
        ),
    ):
        self.path_validation_service = path_validation_service
        self.merkle_tree_service = merkle_tree_service
        self.code_chunking_service = code_chunking_service
        self.file_storage_service = file_storage_service
        self.mongodb = mongodb_database
        self.codebase_indexing_use_case = codebase_indexing_use_case
        self.repo_map_service = repo_map_service
        self.repo_map_graphdb_usecase = RepoMapGraphDBUseCase()
        self.extract_nl_context_use_case = extract_nl_context_use_case

    async def extract_nl_context(
        self, codebase_path: str, git_branch_name: str
    ):
        """
        Extract the natural language context from the codebase.
        """
        context = await self.extract_nl_context_use_case.extract_nl_context(
            codebase_path, git_branch_name
        )
        return context

    async def generate_repo_map(self, codebase_path: str, git_branch_name: str):
        """
        Generate the repository map for the given codebase path and store it in GraphDB.
        """
        try:
            # Generate repository map and store in GraphDB
            result = (
                await self.repo_map_graphdb_usecase.generate_and_store_repo_map(
                    codebase_path=codebase_path,
                    output_file="intermediate_outputs/repo_map_from_route.json",
                )
            )
            data = {
                "current_codebase_path_should_be": codebase_path,
                "current_git_branch_should_be": git_branch_name,
            }
            await self.file_storage_service.store_variable_in_file_storage(
                data, "fetch_variables.json", codebase_path
            )
            print("✓ Repo map generation completed")

            nl_result = await self.extract_nl_context(
                codebase_path, git_branch_name
            )
            combined_result = {}
            combined_result["repo_map_result"] = result
            combined_result["nl_result"] = nl_result
            return combined_result

        except Exception as e:
            loggers["main"].error(f"Error in generate_repo_map: {e}")
            raise e

    async def get_current_branch_name(self, codebase_path: str) -> str | None:
        """
        Get the current branch name of the git repository at the given codebase path.

        Returns:
            str | None: Branch name if git repository exists, None otherwise
        """
        # Validate if the path exists and is accessible
        self.path_validation_service.validate_codebase_path(codebase_path)

        # Check if it's a git repository
        if not self.path_validation_service.validate_git_repository(
            codebase_path
        ):
            context_variable_git_branch_name.set("default")
            return "default"

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    codebase_path,
                    "rev-parse",
                    "--abbrev-ref",
                    "HEAD",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            current_git_branch = result.stdout.decode("utf-8").strip()

            context_variable_git_branch_name.set(current_git_branch)

            return current_git_branch

        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode("utf-8").strip()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get current branch name: {error_message}",
            )

    async def chunking_and_storage(
        self, codebase_path: str, git_branch_name: str
    ):
        """
        Chunk the codebase and store the chunks in the database
        """
        # Create storage key for the merkle tree
        storage_key = f"{codebase_path}:{git_branch_name}"

        # Initialize statistics
        stats = {
            "git_branch": git_branch_name,
            "codebase_path": codebase_path,
        }

        # Build current merkle tree
        current_tree, current_file_hashes = (
            self.merkle_tree_service.build_merkle_tree(codebase_path)
        )

        # Check if we have a previous merkle tree
        previous_data = self.file_storage_service.get_merkle_tree(storage_key)

        # Files that need processing
        files_to_process = []
        files_to_delete = []

        if previous_data:
            previous_tree, previous_file_hashes = previous_data

            # Compare trees to find changed files
            changed_files, deleted_files = (
                self.merkle_tree_service.compare_merkle_trees(
                    previous_tree,
                    current_tree,
                    previous_file_hashes,
                    current_file_hashes,
                )
            )
            if not changed_files and not deleted_files:
                data = await self.file_storage_service.get_variable_from_file_storage(
                    "fetch_variables.json", codebase_path
                )
                if git_branch_name == data.get(
                    "current_git_branch_should_be", "default "
                ) and codebase_path == data.get(
                    "current_codebase_path_should_be", codebase_path
                ):
                    return stats
                else:
                    repo_map_results = await self.generate_repo_map(
                        codebase_path, git_branch_name
                    )
                    combined_result = {}
                    combined_result["repo_map_result"] = repo_map_results[
                        "repo_map_result"
                    ]
                    combined_result["nl_result"] = repo_map_results["nl_result"]
                    return combined_result

            # Only process changed files
            files_to_process = [
                os.path.join(codebase_path, file_path)
                for file_path in changed_files
            ]
            files_to_delete = [
                os.path.join(codebase_path, file_path)
                for file_path in deleted_files
            ]
            stats["changed_files"] = changed_files
            stats["deleted_files"] = deleted_files

        else:
            # Process all files if no previous tree
            files_to_process = [
                os.path.join(codebase_path, file_path)
                for file_path in current_file_hashes.keys()
            ]
            stats["changed_files"] = list(current_file_hashes.keys())

        stats["total_files_processed"] = len(files_to_process)

        with open(
            "intermediate_outputs/rag_context_gather_outputs/files_to_process.json",
            "w",
        ) as f:
            json.dump(files_to_process, f, indent=2)
        with open(
            "intermediate_outputs/rag_context_gather_outputs/files_to_delete.json",
            "w",
        ) as f:
            json.dump(files_to_delete, f, indent=2)

        # Process files and generate chunks
        all_chunks = []
        for file_path in files_to_process:
            chunks = self.code_chunking_service.chunk_file(
                file_path, codebase_path, git_branch_name
            )
            all_chunks.extend(chunks)

        stats["total_chunks_created"] = len(all_chunks)

        codebase_path_hash = calculate_hash(codebase_path)

        # Convert absolute paths in files_to_delete to relative paths
        relative_files_to_delete = get_relative_paths(
            files_to_delete, codebase_path
        )

        data = {
            "codebase_path_name": codebase_path,
            "codebase_path_hash": codebase_path_hash,
            "chunks": all_chunks,
            "deleted_file_paths": relative_files_to_delete,
            "current_git_branch": git_branch_name,
        }

        # Run both operations in parallel since they are independent
        loggers["main"].info(
            "🚀 Starting parallel execution of codebase indexing and repo map generation..."
        )

        # Create tasks for parallel execution
        indexing_task = asyncio.create_task(
            self.codebase_indexing_use_case.process_codebase_chunks(data),
            name="codebase_indexing",
        )

        repo_map_task = asyncio.create_task(
            self.generate_repo_map(codebase_path, git_branch_name),
            name="repo_map_generation",
        )

        # Wait for both tasks to complete
        try:
            indexing_result, repo_map_result = await asyncio.gather(
                indexing_task, repo_map_task, return_exceptions=True
            )

            print("✓ Both parallel operations completed")

            # Handle any exceptions
            if isinstance(indexing_result, Exception):
                loggers["main"].error(
                    f"❌ Codebase indexing failed: {indexing_result}"
                )
                raise indexing_result

            if isinstance(repo_map_result, Exception):
                loggers["main"].error(
                    f"❌ Repo map generation failed: {repo_map_result}"
                )
                raise repo_map_result

            # Store the current merkle tree
            self.file_storage_service.store_merkle_tree(
                storage_key, current_tree, current_file_hashes
            )

            # Combine results from both operations
            combined_result = indexing_result.model_dump()
            combined_result["repo_map_result"] = repo_map_result[
                "repo_map_result"
            ]
            combined_result["nl_result"] = repo_map_result["nl_result"]

            return combined_result

        except Exception as e:
            loggers["main"].error(f"❌ Error during parallel execution: {e}")
            raise e
