from typing import Dict, List, Set

from fastapi import Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import IndexModel

from src.app.config.database import mongodb_database
from src.app.config.settings import settings
from src.app.models.domain.chunk import Chunk
from src.app.utils.logging_util import loggers


class ChunkingRepository:
    def __init__(
        self, mongodb_client=Depends(mongodb_database.get_mongo_client)
    ):
        self.mongodb_client = mongodb_client
        self.db_name = settings.MONGODB_DB_NAME

    def _get_collection_name(self, codebase_path_hash: str) -> str:
        """Generate collection name from codebase hash"""
        return f"chunking_{codebase_path_hash}"

    async def _get_or_create_collection(
        self, codebase_path_hash: str
    ) -> AsyncIOMotorCollection:
        """Get or create MongoDB collection for codebase chunks"""
        try:
            collection_name = self._get_collection_name(codebase_path_hash)
            collection = self.mongodb_client[self.db_name][collection_name]

            # Check if collection exists and create indexes if needed
            collections = await self.mongodb_client[
                self.db_name
            ].list_collection_names()
            if collection_name not in collections:
                # Create indexes for efficient querying
                index_models = [
                    IndexModel([("chunk_hash", 1)], unique=True),
                    IndexModel([("git_branch", 1)]),
                    IndexModel([("language", 1)]),
                    IndexModel([("chunk_type", 1)]),
                    IndexModel([("created_at", -1)]),
                ]
                await collection.create_indexes(index_models)
                loggers["main"].info(
                    f"Created new collection '{collection_name}' with indexes"
                )

            return collection

        except Exception as e:
            loggers["main"].error(
                f"Error getting/creating collection for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error accessing codebase collection: {str(e)}",
            )

    async def get_all_chunks(self, codebase_path_hash: str) -> List[Chunk]:
        """Get all chunks from codebase collection"""
        try:
            collection = await self._get_or_create_collection(codebase_path_hash)

            cursor = collection.find({})
            chunks = []

            async for doc in cursor:
                # Remove MongoDB's _id field before converting
                if "_id" in doc:
                    del doc["_id"]
                chunks.append(Chunk.from_dict(doc))

            loggers["main"].info(
                f"Retrieved {len(chunks)} chunks from codebase {codebase_path_hash}"
            )
            return chunks

        except Exception as e:
            loggers["main"].error(
                f"Error retrieving chunks for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500, detail=f"Error retrieving chunks: {str(e)}"
            )

    async def get_existing_chunk_hashes(self, codebase_path_hash: str) -> Set[str]:
        """Get all existing chunk hashes for efficient comparison"""
        try:
            collection = await self._get_or_create_collection(codebase_path_hash)

            # Only fetch chunk_hash field for efficiency
            cursor = collection.find({}, {"chunk_hash": 1, "_id": 0})
            chunk_hashes = set()

            async for doc in cursor:
                chunk_hashes.add(doc["chunk_hash"])

            loggers["main"].info(
                f"Retrieved {len(chunk_hashes)} existing chunk hashes from codebase {codebase_path_hash}"
            )
            return chunk_hashes

        except Exception as e:
            loggers["main"].error(
                f"Error retrieving chunk hashes for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving chunk hashes: {str(e)}",
            )

    async def upsert_chunks_batch(
        self, codebase_path_hash: str, chunks: List[Chunk]
    ) -> Dict[str, int]:
        """Upsert multiple chunks in a single batch operation (without embeddings)"""
        try:
            if not chunks:
                return {"inserted": 0, "updated": 0}

            collection = await self._get_or_create_collection(codebase_path_hash)

            # Prepare bulk operations
            from pymongo import UpdateOne

            operations = []

            for chunk in chunks:
                chunk_dict = chunk.to_dict()
                # Remove embedding from codebase collection (stored separately)
                if "embedding" in chunk_dict:
                    del chunk_dict["embedding"]
                # Remove None values
                chunk_dict = {
                    k: v for k, v in chunk_dict.items() if v is not None
                }

                operations.append(
                    UpdateOne(
                        {"chunk_hash": chunk.chunk_hash},
                        {"$set": chunk_dict},
                        upsert=True,
                    )
                )

            # Execute bulk operation
            result = await collection.bulk_write(operations, ordered=False)

            stats = {
                "inserted": result.upserted_count,
                "updated": result.modified_count,
                "matched": result.matched_count,
            }

            loggers["main"].info(
                f"Batch upsert completed for codebase {codebase_path_hash}: "
                f"inserted={stats['inserted']}, updated={stats['updated']}"
            )

            return stats

        except Exception as e:
            loggers["main"].error(
                f"Error upserting chunks batch for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500, detail=f"Error upserting chunks: {str(e)}"
            )
        
    async def delete_codebase_chunks(self, codebase_path_hash: str) -> int:
        """Delete all chunks for a codebase (cleanup operation)"""
        try:
            collection_name = self._get_collection_name(codebase_path_hash)

            # Drop the entire collection for efficiency
            await self.mongodb_client[self.db_name].drop_collection(
                collection_name
            )

            loggers["main"].info(
                f"Deleted all chunks for codebase {codebase_path_hash}"
            )
            return 1  # Success indicator

        except Exception as e:
            loggers["main"].error(
                f"Error deleting chunks for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting codebase chunks: {str(e)}",
            )

    async def delete_chunks_by_hashes(
        self, codebase_path_hash: str, chunk_hashes: List[str]
    ) -> int:
        """Delete chunks by their hashes (across all branches)"""
        try:
            collection = await self._get_or_create_collection(codebase_path_hash)

            result = await collection.delete_many(
                {"chunk_hash": {"$in": chunk_hashes}}
            )
            deleted_count = result.deleted_count

            loggers["main"].info(
                f"Deleted {deleted_count} chunks by hashes from codebase {codebase_path_hash}"
            )
            return deleted_count

        except Exception as e:
            loggers["main"].error(
                f"Error deleting chunks by hashes for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting chunks by hashes: {str(e)}",
            )

    async def delete_chunks_by_hashes_and_branch(
        self, codebase_path_hash: str, chunk_hashes: List[str], git_branch: str
    ) -> int:
        """Delete chunks by their hashes AND git branch (branch-specific deletion)"""
        try:
            collection = await self._get_or_create_collection(codebase_path_hash)

            result = await collection.delete_many(
                {"chunk_hash": {"$in": chunk_hashes}, "git_branch": git_branch}
            )
            deleted_count = result.deleted_count

            loggers["main"].info(
                f"Deleted {deleted_count} chunks by hashes and branch '{git_branch}' from codebase {codebase_path_hash}"
            )
            return deleted_count

        except Exception as e:
            loggers["main"].error(
                f"Error deleting chunks by hashes and branch for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting chunks by hashes and branch: {str(e)}",
            )

    async def get_chunks_by_file_paths_and_branch(
        self, codebase_path_hash: str, file_paths: List[str], git_branch: str
    ) -> List[Chunk]:
        """Get chunks by their file paths AND git branch"""
        try:
            collection = await self._get_or_create_collection(codebase_path_hash)

            cursor = collection.find(
                {
                    "file_path": {"$in": file_paths},
                    "git_branch": git_branch,
                }
            )
            chunks = []

            async for doc in cursor:
                # Remove MongoDB's _id field before converting
                if "_id" in doc:
                    del doc["_id"]
                chunks.append(Chunk.from_dict(doc))

            loggers["main"].info(
                f"Retrieved {len(chunks)} chunks for {len(file_paths)} obfuscated paths on branch {git_branch} from codebase {codebase_path_hash}"
            )
            return chunks

        except Exception as e:
            loggers["main"].error(
                f"Error retrieving chunks by obfuscated paths and branch for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving chunks by obfuscated paths and branch: {str(e)}",
            )

    async def get_chunk_hashes_by_path_and_branch(
        self, codebase_path_hash: str, file_path: str, git_branch: str
    ) -> Set[str]:
        """Get all chunk hashes for a specific path and branch"""
        try:
            collection = await self._get_or_create_collection(codebase_path_hash)

            cursor = collection.find(
                {
                    "file_path": file_path,
                    "git_branch": git_branch,
                },
                {"chunk_hash": 1, "_id": 0},
            )

            chunk_hashes = set()
            async for doc in cursor:
                chunk_hashes.add(doc["chunk_hash"])

            loggers["main"].info(
                f"Retrieved {len(chunk_hashes)} chunk hashes for path {file_path} on branch {git_branch} from codebase {codebase_path_hash}"
            )
            return chunk_hashes

        except Exception as e:
            loggers["main"].error(
                f"Error retrieving chunk hashes by path and branch for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving chunk hashes by path and branch: {str(e)}",
            )

    async def get_chunks_grouped_by_path_and_branch(
        self, codebase_path_hash: str
    ) -> Dict[str, Dict[str, Set[str]]]:
        """Get all chunks grouped by file_path and git_branch, returning chunk_hashes"""
        try:
            collection = await self._get_or_create_collection(codebase_path_hash)

            cursor = collection.find(
                {},
                {
                    "chunk_hash": 1,
                    "file_path": 1,
                    "git_branch": 1,
                    "_id": 0,
                },
            )

            grouped_chunks = {}
            async for doc in cursor:
                path = doc["file_path"]
                branch = doc["git_branch"]
                chunk_hash = doc["chunk_hash"]

                if path not in grouped_chunks:
                    grouped_chunks[path] = {}
                if branch not in grouped_chunks[path]:
                    grouped_chunks[path][branch] = set()

                grouped_chunks[path][branch].add(chunk_hash)

            loggers["main"].info(
                f"Retrieved chunks grouped by path and branch from codebase {codebase_path_hash}"
            )
            return grouped_chunks

        except Exception as e:
            loggers["main"].error(
                f"Error retrieving grouped chunks for codebase {codebase_path_hash}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving grouped chunks: {str(e)}",
            )
