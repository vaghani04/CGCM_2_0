import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
from fastapi import Depends, HTTPException, status
from src.app.config.settings import settings
from src.app.models.domain.chunk import Chunk
from src.app.models.schemas.chunk_indexing_schema import ChunkData
from src.app.repositories.chunking_repository import ChunkingRepository
from src.app.repositories.embedding_repository import EmbeddingRepository
from src.app.services.embedding_service import EmbeddingService
from src.app.services.pinecone_service import PineconeService
from src.app.utils.logging_util import loggers
from src.app.utils.hash_calculator import calculate_special_hash


class CodebaseIndexingService:
    def __init__(
        self,
        chunking_repository: ChunkingRepository = Depends(ChunkingRepository),
        embedding_repository: EmbeddingRepository = Depends(
            EmbeddingRepository
        ),
        embedding_service: EmbeddingService = Depends(EmbeddingService),
        pinecone_service: PineconeService = Depends(PineconeService),
    ):
        self.chunking_repository = chunking_repository
        self.embedding_repository = embedding_repository
        self.embedding_service = embedding_service
        self.pinecone_service = pinecone_service

        self.embeddings_model_name = settings.VOYAGEAI_EMBEDDINGS_MODEL
        self.embeddings_dimension = settings.EMBEDDINGS_DIMENSION
        self.similarity_metric = settings.INDEXING_SIMILARITY_METRIC
        self.embeddings_batch_size = settings.EMBEDDINGS_BATCH_SIZE
        self.upsert_batch_size = settings.INDEXING_UPSERT_BATCH_SIZE
        self.semaphore = asyncio.Semaphore(settings.INDEXING_SEMAPHORE_VALUE)

    async def identify_and_prepare_chunks_with_embeddings(
        self, codebase_path_hash: str, incoming_chunks: List[ChunkData]
    ) -> Tuple[List[Chunk], List[ChunkData], int]:
        """Identify chunks and prepare them with embeddings from global collection or generate new ones"""
        try:
            incoming_hashes = [chunk.content_hash for chunk in incoming_chunks]

            # Get existing embeddings from global collection
            existing_embeddings = (
                await self.embedding_repository.get_embeddings_by_hashes(
                    incoming_hashes
                )
            )

            # Separate chunks that need new embeddings vs those with existing embeddings
            chunks_needing_embeddings = []
            chunks_with_embeddings = []

            for chunk_data in incoming_chunks:
                if chunk_data.content_hash in existing_embeddings:
                    chunk = Chunk(
                        chunk_hash=chunk_data.chunk_hash,
                        content_hash=chunk_data.content_hash,
                        content=chunk_data.content,
                        file_path=chunk_data.file_path,
                        start_line=chunk_data.start_line,
                        end_line=chunk_data.end_line,
                        language=chunk_data.language,
                        chunk_type=chunk_data.chunk_type,
                        git_branch=chunk_data.git_branch,
                        token_count=chunk_data.token_count,
                        embedding=existing_embeddings[chunk_data.content_hash],
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                    chunks_with_embeddings.append(chunk)
                else:
                    # Needs new embedding
                    chunks_needing_embeddings.append(chunk_data)

            # Generate embeddings for chunks that need them
            new_embeddings_generated = 0
            if chunks_needing_embeddings:
                new_chunks_with_embeddings = (
                    await self.generate_embeddings_for_chunks(
                        chunks_needing_embeddings
                    )
                )
                chunks_with_embeddings.extend(new_chunks_with_embeddings)
                new_embeddings_generated = len(new_chunks_with_embeddings)

                # Store new embeddings in global collection
                embeddings_to_store = []
                for chunk in new_chunks_with_embeddings:
                    embeddings_to_store.append(
                        {
                            "content_hash": chunk.content_hash,
                            "embedding": chunk.embedding,
                        }
                    )

                if embeddings_to_store:
                    await self.embedding_repository.store_embeddings_batch(
                        embeddings_to_store
                    )

            loggers["main"].info(
                f"Chunk processing for codebase {codebase_path_hash}: "
                f"total={len(incoming_chunks)}, reused_embeddings={len(existing_embeddings)}, "
                f"new_embeddings={new_embeddings_generated}"
            )

            return (
                chunks_with_embeddings,
                chunks_needing_embeddings,
                new_embeddings_generated,
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error identifying and preparing chunks: {str(e)}",
            )

    async def _process_embedding_chunk(
        self, contents: List[str]
    ) -> List[List[float]]:
        """Process a batch of content for embeddings"""
        async with self.semaphore:
            try:
                # print("reached here to create dummy embeddings")
                # import random
                # embeddings = []
                # for content in contents:
                #     # Generate random embedding vector with specified dimension
                #     dummy_embedding = [random.random() for _ in range(self.embeddings_dimension)]
                #     embeddings.append(dummy_embedding)
                # return embeddings

                embeddings = (
                    await self.embedding_service.voyageai_dense_embeddings(
                        self.embeddings_model_name, self.embeddings_dimension, contents
                    )
                )
                return embeddings
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error generating embeddings: {str(e)}",
                )

    async def generate_embeddings_for_chunks(
        self, new_chunks: List[ChunkData]
    ) -> List[Chunk]:
        """Generate embeddings for new chunks"""
        try:
            if not new_chunks:
                return []

            loggers["main"].info(
                f"Generating embeddings for {len(new_chunks)} new chunks"
            )

            contents = [chunk.content for chunk in new_chunks]

            all_embeddings = []
            content_batches = [
                contents[i : i + self.embeddings_batch_size]
                for i in range(0, len(contents), self.embeddings_batch_size)
            ]

            tasks = [
                self._process_embedding_chunk(batch)
                for batch in content_batches
            ]

            batch_results = await asyncio.gather(*tasks)

            for batch_embeddings in batch_results:
                all_embeddings.extend(batch_embeddings)

            chunks_with_embeddings = []
            for i, chunk_data in enumerate(new_chunks):
                chunk = Chunk(
                    chunk_hash=chunk_data.chunk_hash,
                    content_hash=chunk_data.content_hash,
                    content=chunk_data.content,
                    file_path=chunk_data.file_path,
                    start_line=chunk_data.start_line,
                    end_line=chunk_data.end_line,
                    language=chunk_data.language,
                    chunk_type=chunk_data.chunk_type,
                    git_branch=chunk_data.git_branch,
                    token_count=chunk_data.token_count,
                    embedding=all_embeddings[i],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                chunks_with_embeddings.append(chunk)

            loggers["main"].info(
                f"Successfully generated embeddings for {len(chunks_with_embeddings)} chunks"
            )
            return chunks_with_embeddings

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating embeddings for chunks: {str(e)}",
            )

    async def store_chunks_in_mongodb(
        self, codebase_path_hash: str, chunks: List[Chunk]
    ) -> Dict[str, int]:
        """Store chunks with embeddings in MongoDB"""
        try:
            if not chunks:
                return {"inserted": 0, "updated": 0}

            loggers["main"].info(
                f"Storing {len(chunks)} chunks in MongoDB for codebase {codebase_path_hash}"
            )

            result = await self.chunking_repository.upsert_chunks_batch(
                codebase_path_hash, chunks
            )

            loggers["main"].info(
                f"Successfully stored chunks in MongoDB: "
                f"inserted={result['inserted']}, updated={result['updated']}"
            )

            return result

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error storing chunks in MongoDB: {str(e)}",
            )

    async def _get_or_create_pinecone_index(self, codebase_path_hash: str) -> str:
        """Get or create Pinecone index for codebase"""
        try:
            index_name = codebase_path_hash

            # List existing indexes
            list_result = await self.pinecone_service.list_pinecone_indexes()
            indexes = list_result.get("indexes", [])
            index_names = [index.get("name") for index in indexes]

            if index_name not in index_names:
                # Create new index
                loggers["main"].info(
                    f"Creating new Pinecone index: {index_name}"
                )
                create_result = await self.pinecone_service.create_index(
                    index_name=index_name,
                    dimension=self.embeddings_dimension,
                    metric=self.similarity_metric,
                )
                return create_result.get("host")
            else:
                # Get existing index host
                for index in indexes:
                    if index.get("name") == index_name:
                        loggers["main"].info(
                            f"Using existing Pinecone index: {index_name}"
                        )
                        return index.get("host")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not get index host",
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error with Pinecone index: {str(e)}",
            )

    async def _upsert_batch_to_pinecone(
        self, index_host: str, batch: List[Chunk], namespace: str
    ) -> Dict:
        """Upsert a batch of chunks to Pinecone"""
        try:
            if not batch:
                return {"upserted_count": 0}

            embeddings = [chunk.embedding for chunk in batch]

            chunk_dicts = []
            for chunk in batch:
                chunk_dict = chunk.to_dict()
                # Add ID for pinecone
                chunk_dict["_id"] = f"{chunk.chunk_hash}_{chunk.git_branch}"
                chunk_dicts.append(chunk_dict)

            # Format for Pinecone upsert
            upsert_data = await self.pinecone_service.upsert_format(
                chunk_dicts, embeddings
            )

            # Upsert to Pinecone
            result = await self.pinecone_service.upsert_vectors(
                index_host, upsert_data, namespace
            )

            return result

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error upserting to Pinecone: {str(e)}",
            )

    async def upsert_chunks_to_pinecone(
        self, codebase_path_hash: str, all_chunks: List[Chunk], git_branch: str
    ) -> Dict[str, int]:
        """Upsert all chunks to Pinecone vector database"""
        try:
            if not all_chunks:
                return {"upserted_count": 0, "batches_processed": 0}

            loggers["main"].info(
                f"Upserting {len(all_chunks)} chunks to Pinecone for codebase {codebase_path_hash}"
            )

            index_host = await self._get_or_create_pinecone_index(
                codebase_path_hash
            )

            namespace = git_branch if git_branch else "default"

            batches = [
                all_chunks[i : i + self.upsert_batch_size]
                for i in range(0, len(all_chunks), self.upsert_batch_size)
            ]

            total_upserted = 0
            for i, batch in enumerate(batches):
                loggers["main"].info(
                    f"Processing Pinecone batch {i+1}/{len(batches)}"
                )

                result = await self._upsert_batch_to_pinecone(
                    index_host, batch, namespace
                )

                if "upsertedCount" in result:
                    total_upserted += result["upsertedCount"]
                elif "upserted_count" in result:
                    total_upserted += result["upserted_count"]

            # Add small delay for Pinecone processing
            time.sleep(2)

            loggers["main"].info(
                f"Successfully upserted {total_upserted} vectors to Pinecone in {len(batches)} batches"
            )

            return {
                "upserted_count": total_upserted,
                "batches_processed": len(batches),
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error upserting chunks to Pinecone: {str(e)}",
            )

    async def handle_chunk_level_deletion(
        self, codebase_path_hash: str, incoming_chunks: List[ChunkData], 
        codebase_path_name: str
    ) -> Tuple[int, int]:
        """Handle deletion of individual chunks that are no longer present"""
        try:
            if not incoming_chunks:
                loggers["main"].info(
                    "No incoming chunks, skipping chunk-level deletion"
                )
                return 0, 0

            # Group incoming chunks by git_branch and file_path
            incoming_grouped = {}
            for chunk in incoming_chunks:
                path = chunk.file_path
                branch = chunk.git_branch

                if path not in incoming_grouped:
                    incoming_grouped[path] = {}
                if branch not in incoming_grouped[path]:
                    incoming_grouped[path][branch] = set()

                incoming_grouped[path][branch].add(chunk.chunk_hash)

            # Only process deletions for paths that are present in the incoming payload
            mongodb_deleted_count = 0
            pinecone_deleted_count = 0

            loggers["main"].info(
                f"Processing chunk deletion for {len(incoming_grouped)} unique paths in incoming payload"
            )

            for path, branches_in_path in incoming_grouped.items():
                loggers["main"].info(
                    f"Processing path: '{path}' with {len(branches_in_path)} branches: {list(branches_in_path.keys())}"
                )

                for branch, incoming_hashes in branches_in_path.items():
                    loggers["main"].info(
                        f"Processing branch '{branch}' for path '{path}' - incoming: {len(incoming_hashes)} chunks"
                    )

                    # Get existing chunks for this specific path and branch only
                    existing_hashes = await self.chunking_repository.get_chunk_hashes_by_path_and_branch(
                        codebase_path_hash, path, branch
                    )

                    loggers["main"].info(
                        f"Found {len(existing_hashes)} existing chunks for path '{path}' on branch '{branch}'"
                    )

                    # Find chunks that exist in DB but are missing in the incoming payload
                    hashes_to_delete = existing_hashes - incoming_hashes

                    if hashes_to_delete:
                        hashes_to_delete_list = list(hashes_to_delete)

                        loggers["main"].info(
                            f"DELETING {len(hashes_to_delete)} chunks for path '{path}' ONLY from branch '{branch}'"
                        )

                        # Delete from MongoDB codebase collection (branch-specific)
                        mongodb_deleted = await self.chunking_repository.delete_chunks_by_hashes_and_branch(
                            codebase_path_hash, hashes_to_delete_list, branch
                        )
                        mongodb_deleted_count += mongodb_deleted

                        # Delete from Pinecone (branch-specific namespace)
                        pinecone_deleted = (
                            await self._delete_chunks_from_pinecone(
                                codebase_path_hash, hashes_to_delete_list, branch, codebase_path_name
                            )
                        )
                        pinecone_deleted_count += pinecone_deleted

                        loggers["main"].info(
                            f"Successfully deleted {mongodb_deleted} from MongoDB and {pinecone_deleted} from Pinecone namespace '{branch}'"
                        )
                    else:
                        loggers["main"].info(
                            f"No chunks to delete for path '{path}' on branch '{branch}' - all chunks are up to date"
                        )

            if mongodb_deleted_count == 0 and pinecone_deleted_count == 0:
                loggers["main"].info(
                    "No individual chunks needed to be deleted"
                )
            else:
                loggers["main"].info(
                    f"Successfully deleted {mongodb_deleted_count} chunks from codebase collection and {pinecone_deleted_count} from Pinecone"
                )

            return mongodb_deleted_count, pinecone_deleted_count

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error handling chunk-level deletion: {str(e)}",
            )

    async def handle_deleted_files(
        self,
        codebase_path_hash: str,
        delete_file_paths: List[str],
        codebase_path_name: str,
        current_git_branch: str = "default",
    ) -> Tuple[int, int]:
        """Handle deletion of chunks for deleted files in specific git branch"""
        try:
            if not delete_file_paths:
                return 0, 0

            loggers["main"].info(
                f"Handling branch-specific deletion for {len(delete_file_paths)} files in codebase {codebase_path_hash} on branch {current_git_branch}"
            )

            # Step 1: Find chunks with matching file paths & git branch
            chunks_to_delete = await self.chunking_repository.get_chunks_by_file_paths_and_branch(
                codebase_path_hash,
                delete_file_paths,
                current_git_branch
            )

            # with open("intermediate_outputs/chunks_to_delete.json", "w") as f:
            #     json.dump(chunks_to_delete, f, indent=2)

            if not chunks_to_delete:
                loggers["main"].info(
                    "No chunks found for deleted files in the specified branch"
                )
                return 0, 0

            chunk_hashes_to_delete = [
                chunk.chunk_hash for chunk in chunks_to_delete
            ]

            loggers["main"].info(
                f"Found {len(chunks_to_delete)} chunks to delete for {len(delete_file_paths)} deleted files on branch {current_git_branch}"
            )

            # Step 2: Delete from MongoDB codebase collection based on branch-specific
            mongodb_deleted_count = 0
            if chunk_hashes_to_delete:
                mongodb_deleted_count = await self.chunking_repository.delete_chunks_by_hashes_and_branch(
                    codebase_path_hash, chunk_hashes_to_delete, current_git_branch
                )

            # Step 3: Delete from Pinecone based on branch-specific namespace
            pinecone_deleted_count = 0
            if chunk_hashes_to_delete:
                pinecone_deleted_count = (
                    await self._delete_chunks_from_pinecone(
                        codebase_path_hash,
                        chunk_hashes_to_delete,
                        current_git_branch,
                        codebase_path_name
                    )
                )

            loggers["main"].info(
                f"Successfully deleted {mongodb_deleted_count} chunks from MongoDB and {pinecone_deleted_count} vectors from Pinecone on branch {current_git_branch}"
            )

            return mongodb_deleted_count, pinecone_deleted_count

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error handling deleted files in codebase_indexing_service: {str(e)}",
            )

    async def _delete_chunks_from_pinecone(
        self, codebase_path_hash: str, chunk_hashes: List[str], git_branch: str, codebase_path_name: str
    ) -> int:
        """Delete specific chunks from Pinecone by hash"""
        try:
            if not chunk_hashes:
                return 0

            codebase_dir_path = codebase_path_name.split('/')[-1]
            codebase_path_hash_special_hash = calculate_special_hash(codebase_path_name)
            pinecone_index_name = f"{codebase_dir_path.lower().replace('_', '-')}-{codebase_path_hash_special_hash}"
            index_host = await self._get_or_create_pinecone_index(
                pinecone_index_name
            )

            # Use git_branch as namespace
            namespace = git_branch if git_branch else "default"

            total_deleted = 0

            for i in range(0, len(chunk_hashes), self.upsert_batch_size):
                batch_hashes = chunk_hashes[i : i + self.upsert_batch_size]

                try:
                    result = await self.pinecone_service.delete_vectors(
                        index_host, batch_hashes, namespace
                    )

                    if isinstance(result, dict) and "deleted" in result:
                        total_deleted += result["deleted"]
                    else:
                        total_deleted += len(batch_hashes)

                except Exception as e:
                    loggers["main"].warning(
                        f"Failed to delete batch {i//self.upsert_batch_size + 1} from Pinecone: {str(e)}"
                    )

            loggers["main"].info(
                f"Deleted {total_deleted} vectors from Pinecone namespace '{namespace}'"
            )

            return total_deleted

        except Exception as e:
            loggers["main"].error(
                f"Error deleting chunks from Pinecone: {str(e)}"
            )
            return 0
