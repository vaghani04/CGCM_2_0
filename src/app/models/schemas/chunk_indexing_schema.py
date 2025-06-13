from typing import List

from pydantic import BaseModel, Field


class ChunkData(BaseModel):
    chunk_hash: str = Field(..., description="Unique hash of the chunk")
    content_hash: str = Field(..., description="Unique hash of the chunk content")
    content: str = Field(..., description="The actual content of the chunk")
    file_path: str = Field(..., description="file path")
    start_line: int = Field(..., description="Starting line number")
    end_line: int = Field(..., description="Ending line number")
    language: str = Field(..., description="Programming language")
    chunk_type: str = Field(
        default=[], description="Type of chunk (code, txt, etc.)"
    )
    git_branch: str = Field(..., description="Git branch name")
    token_count: int = Field(..., description="Number of tokens in the chunk")


class ChunkProcessingStats(BaseModel):
    total_chunks: int = Field(
        ..., description="Total number of chunks received"
    )
    existing_chunks: int = Field(
        ..., description="Number of chunks already in database"
    )
    new_chunks: int = Field(..., description="Number of new chunks processed")
    deleted_chunks: int = Field(
        default=0, description="Number of chunks deleted from deleted files"
    )
    embeddings_generated: int = Field(
        ..., description="Number of embeddings generated"
    )
    pinecone_upserted: int = Field(
        ..., description="Number of vectors upserted to Pinecone"
    )
    pinecone_deleted: int = Field(
        default=0, description="Number of vectors deleted from Pinecone"
    )


class CodebaseIndexingResponse(BaseModel):
    success: bool = Field(
        ..., description="Whether the operation was successful"
    )
    message: str = Field(..., description="Response message")
    codebase_path_hash: str = Field(
        ..., description="Codebase path that was processed"
    )
    git_branch: str = Field(..., description="Git branch used for indexing")
    stats: ChunkProcessingStats = Field(
        ..., description="Processing statistics"
    )
    processing_time_seconds: float = Field(
        ..., description="Total processing time"
    )
