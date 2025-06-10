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

    # Repository Map settings
    REPO_MAP_OUTPUT_FILE: str = "final_repo_map.json"
    REPO_MAP_SUPPORTED_EXTENSIONS: list = [".py", ".js", ".jsx", ".ts", ".tsx"]
    REPO_MAP_EXCLUDED_DIRS: list = ["node_modules", "__pycache__", ".git", ".venv", "venv", "env", "build", "dist", ".next", "target", "bin", "obj"]
    REPO_MAP_MAX_FILE_SIZE_MB: int = 5
    REPO_MAP_CHUNK_SIZE: int = 1000

    # Voyage Settings
    VOYAGEAI_API_KEY: str = "sdf"
    VOYAGEAI_BASE_URL: str = "https://api.voyageai.com/v1"

    # Neo4j Graph Database settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"
    
    # GraphDB settings
    GRAPHDB_BATCH_SIZE: int = 100
    GRAPHDB_MAX_RETRIES: int = 3
    GRAPHDB_RETRY_DELAY: int = 1

    # OpenAI settings
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_COMPLETION_ENDPOINT: str = "/chat/completions"
    OPENAI_MODEL: str = "gpt-4.1-mini"

    class Config:
        env_file = ".env"


settings = Settings()