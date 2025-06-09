from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "cgcm_2_0"
    LLM_USAGE_COLLECTION_NAME: str = "llm_usage"
    EMBEDDINGS_COLLECTION_NAME: str = "global_embeddings_collection"
    
    # Pinecone settings
    PINECONE_API_KEY: str
    PINECONE_CREATE_INDEX_URL: str = "https://api.pinecone.io/indexes"
    PINECONE_API_VERSION: str = "2025-01"
    PINECONE_EMBED_URL: str = "https://api.pinecone.io/embed"
    PINECONE_UPSERT_URL: str = "https://{}/vectors/upsert"
    PINECONE_RERANK_URL: str = "https://api.pinecone.io/rerank"
    PINECONE_QUERY_URL: str = "https://{}/query"
    PINECONE_LIST_INDEXES_URL: str = "https://api.pinecone.io/indexes"

    # Indexing settings
    INDEXING_UPSERT_BATCH_SIZE: int = 80
    INDEXING_SIMILARITY_METRIC: str = "dotproduct"
    INDEXING_SEMAPHORE_VALUE: int = 7

    # Codebase indexing settings
    EMBEDDINGS_BATCH_SIZE: int = 80
    EMBEDDINGS_DIMENSION: int = 1024
    EMBEDDINGS_MODEL: str = "voyage-code-3"

    # Voyage Settings
    VOYAGEAI_API_KEY: str = "sdf"
    VOYAGEAI_BASE_URL: str = "https://api.voyageai.com/v1"

    class Config:
        env_file = ".env"


settings = Settings()