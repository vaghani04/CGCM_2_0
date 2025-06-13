import time
from datetime import datetime
from typing import Dict

from fastapi import Depends, HTTPException, status

from src.app.models.schemas.chunk_indexing_schema import (
    ChunkData,
    ChunkProcessingStats,
    CodebaseIndexingResponse,
)
from src.app.utils.logging_util import loggers
from src.app.services.codebase_indexing_service import CodebaseIndexingService
from src.app.utils.hash_calculator import calculate_special_hash


class CodebaseIndexingUseCase:
    def __init__(
        self,
        codebase_idnexing_service: CodebaseIndexingService = Depends(
            CodebaseIndexingService
        ),
    ):
        self.codebase_indexing_service = codebase_idnexing_service

    async def process_codebase_chunks(
        self, data: Dict
    ) -> CodebaseIndexingResponse:
        """Main orchestration method for processing codebase chunks"""
        start_time = time.time()

        try:
            loggers["main"].info("Starting codebase chunk processing")

            # Parse request data
            codebase_path_hash = data.get("codebase_path_hash")
            chunks_data = data.get("chunks", [])
            deleted_file_paths = data.get(
                "deleted_file_paths", []
            )
            current_git_branch = data.get(
                "current_git_branch", "default"
            )
            codebase_path_name = data.get("codebase_path_name")
            codebase_dir_path = codebase_path_name.split('/')[-1]

            if not codebase_path_hash:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="codebase_path_hash is required",
                )

            loggers["main"].info(
                f"Processing {len(chunks_data)} chunks and {len(deleted_file_paths)} deleted files for codebase {codebase_path_hash} on branch {current_git_branch}"
            )

            # Step-1: chunk level insertion
            chunk_objects = []
            if chunks_data:
                for chunk_dict in chunks_data:
                    try:
                        chunk_obj = ChunkData(**chunk_dict)
                        chunk_objects.append(chunk_obj)
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid chunk data: {str(e)}",
                        )

            # Step-2: file level deletion
            deleted_files_count = 0
            pinecone_deleted_files_count = 0
            if deleted_file_paths:
                deleted_files_count, pinecone_deleted_files_count = (
                    await self.codebase_indexing_service.handle_deleted_files(
                        codebase_path_hash,
                        deleted_file_paths,
                        codebase_path_name,
                        current_git_branch,
                    )
                )

            # Step-3: chunk level deletion
            deleted_chunks_count = 0
            pinecone_deleted_chunks_count = 0
            if (
                chunk_objects
            ):
                deleted_chunks_count, pinecone_deleted_chunks_count = (
                    await self.codebase_indexing_service.handle_chunk_level_deletion(
                        codebase_path_hash, chunk_objects, codebase_path_name
                    )
                )

            # Step-4: prepare embeddings
            (
                all_chunks_with_embeddings,
                chunks_needing_new_embeddings,
                embeddings_generated,
            ) = await self.codebase_indexing_service.identify_and_prepare_chunks_with_embeddings(
                codebase_path_hash, chunk_objects
            )

            # Step-5: store in mongodb
            mongodb_result = {"inserted": 0, "updated": 0}
            if all_chunks_with_embeddings:
                mongodb_result = await self.codebase_indexing_service.store_chunks_in_mongodb(
                    codebase_path_hash, all_chunks_with_embeddings
                )

            # Step 6: pinecone upsertion
            all_chunks_for_pinecone = all_chunks_with_embeddings

            git_branch = "default"
            if chunk_objects:
                git_branch = chunk_objects[0].git_branch or "default"

            pinecone_result = {"upserted_count": 0, "batches_processed": 0}

            codebase_path_hash_special_hash = calculate_special_hash(codebase_path_name)
            pinecone_index_name = f"{codebase_dir_path.lower().replace('_', '-')}-{codebase_path_hash_special_hash}"
            if all_chunks_for_pinecone:
                pinecone_result = await self.codebase_indexing_service.upsert_chunks_to_pinecone(
                    pinecone_index_name, all_chunks_for_pinecone, git_branch
                )

            processing_time = time.time() - start_time

            total_deleted_chunks = deleted_files_count + deleted_chunks_count
            total_pinecone_deleted = (
                pinecone_deleted_files_count + pinecone_deleted_chunks_count
            )

            # Create statistics
            stats = ChunkProcessingStats(
                total_chunks=len(chunk_objects),
                existing_chunks=len(chunk_objects)
                - len(chunks_needing_new_embeddings),
                new_chunks=len(chunks_needing_new_embeddings),
                deleted_chunks=total_deleted_chunks,
                embeddings_generated=embeddings_generated,
                pinecone_upserted=pinecone_result["upserted_count"],
                pinecone_deleted=total_pinecone_deleted,
            )

            # Create response
            response = CodebaseIndexingResponse(
                success=True,
                message="Codebase chunks processed successfully",
                codebase_path_hash=codebase_path_hash,
                git_branch=git_branch,
                stats=stats,
                processing_time_seconds=round(processing_time, 2),
            )

            loggers["main"].info(
                f"Codebase indexing completed successfully for {codebase_path_hash}. "
                f"Time: {processing_time:.2f}s, New embeddings: {len(chunks_needing_new_embeddings)}, "
                f"Reused embeddings: {len(chunk_objects) - len(chunks_needing_new_embeddings)}, "
                f"Deleted: {total_deleted_chunks}, Pinecone: {pinecone_result['upserted_count']}"
            )

            return response

        except HTTPException:
            raise
        except Exception as e:
            loggers["main"].error(
                f"Unexpected error in codebase indexing: {str(e)}"
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error processing codebase chunks: {str(e)}",
            )

    async def get_codebase_stats(self, codebase_path_hash: str) -> Dict:
        """Get statistics about a codebase's indexed chunks"""
        try:
            loggers["main"].info(
                f"Getting stats for codebase {codebase_path_hash}"
            )

            # Get all chunks for the codebase
            chunks = await self.codebase_indexing_service.chunk_repository.get_all_chunks(
                codebase_path_hash
            )

            # Calculate statistics
            total_chunks = len(chunks)
            languages = {}
            chunk_types = {}
            git_branches = {}

            for chunk in chunks:
                # Count by language
                languages[chunk.language] = languages.get(chunk.language, 0) + 1

                # Count by chunk type
                chunk_types[chunk.chunk_type] = (
                    chunk_types.get(chunk.chunk_type, 0) + 1
                )

                # Count by git branch
                git_branches[chunk.git_branch] = (
                    git_branches.get(chunk.git_branch, 0) + 1
                )

            stats = {
                "codebase_path_hash": codebase_path_hash,
                "total_chunks": total_chunks,
                "languages": languages,
                "chunk_types": chunk_types,
                "git_branches": git_branches,
                "last_updated": datetime.now().isoformat(),
            }

            loggers["main"].info(
                f"Retrieved stats for codebase {codebase_path_hash}: {total_chunks} chunks"
            )

            return stats

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting codebase stats: {str(e)}",
            )

    async def get_embedding_stats(self) -> Dict:
        """Get statistics about the global embedding collection"""
        try:
            loggers["main"].info("Getting global embedding stats")

            # Get embedding statistics
            stats = (
                await self.codebase_indexing_service.embedding_repository.get_embedding_stats()
            )

            loggers["main"].info(
                f"Retrieved global embedding stats: {stats['total_embeddings']} embeddings"
            )

            return stats

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting embedding stats: {str(e)}",
            )