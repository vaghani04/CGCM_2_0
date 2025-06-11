import time
import random
from fastapi import Depends
import json
from src.app.services.embedding_service import (
    EmbeddingService,
)
from src.app.services.pinecone_service import (
    PineconeService,
)
from src.app.services.re_ranking_service import (
    RerankerService,
)
from src.app.config.settings import settings


class RAGRetrievalUsecase:
    def __init__(
        self,
        embedding_service: EmbeddingService = Depends(EmbeddingService),
        pinecone_service: PineconeService = Depends(PineconeService),
        reranker_service: RerankerService = Depends(RerankerService),
    ):
        self.embedding_service = embedding_service
        self.pinecone_service = pinecone_service
        self.reranker_service = reranker_service
        self.embedding_model = "voyage-code-3"
        self.reranker_model = "rerank-2"
        self.similarity_metric = settings.INDEXING_SIMILARITY_METRIC
        self.dimension = 1024
        self.query_input_type = "query"
        self.top_k = 15
        self.top_n = 8

    async def perform_rag(self, query: str, index_name: str, target_directories: list[str]):

        # Step 1: Generate embeddings for the query
        query_embedding = (
            await self.embedding_service.voyageai_dense_embeddings(
                self.embedding_model,
                dimension=self.dimension,
                inputs=[query],
                input_type=self.query_input_type,
            )
        )
        # query_embedding = [random.random() for _ in range(self.dimension)]
        query_embedding = query_embedding[0]

        # Step 2: Query Pinecone with the embeddings
        # Create metadata filter based on target directories if provided
        filter_conditions = {}
        if target_directories and len(target_directories) > 0:
            filter_conditions = {"directory": {"$in": target_directories}}
        index_host = await self.pinecone_service.get_index_host(index_name)

        vector_search_results = await self.pinecone_service.pinecone_query(
            index_host=index_host,
            top_k=self.top_k,
            vector=query_embedding,
            include_metadata=True,
            filter_dict=filter_conditions,
        )

        # return vector_search_results

        if not vector_search_results or not vector_search_results.get(
            "matches"
        ):
            return []

        # Step 3: Extract text passages and metadata from results
        documents = []
        doc_metadata = []
        file_paths = []
        for match in vector_search_results.get("matches", []):
            if match.get("metadata"):
                doc_metadata.append(
                    {
                        "score": match.get("score", 0),
                        "file_path": match.get("metadata", {}).get(
                            "file_path", "unknown"
                        ),
                        "start_line": match.get("metadata", {}).get(
                            "start_line", "unknown"
                        ),
                        "end_line": match.get("metadata", {}).get(
                            "end_line", "unknown"
                        ),
                        "file_name": match.get("metadata", {}).get(
                            "file_name", "unknown"
                        ),
                    }
                )
        with open("intermediate_outputs/pinecone_retrieval_results.json", "w") as f:
            json.dump(doc_metadata, f, indent=2)
        return doc_metadata

        if not documents:
            return []

        reranked_results = await self.reranker_service.voyage_rerank(
            self.reranker_model, query, documents, self.top_n
        )

        # Step 5: Combine reranked results with metadata
        final_results = []
        for result in reranked_results.get("data", []):
            index = result.get("index")
            if index is not None and 0 <= index < len(doc_metadata):
                final_results.append(
                    {
                        "text": documents[index],
                        "relevance_score": result.get("relevance_score", 0),
                        "metadata": doc_metadata[index],
                    }
                )

        full_final_results = final_results
        return full_final_results

    async def rag_retrieval(self, query: str, index_name: str, target_directories: list[str] = []):
        start_time = time.time()

        retrieved_docs = await self.perform_rag(query, index_name, target_directories)

        # Step 3: Format and return the final response
        end_time = time.time()
        processing_time = end_time - start_time

        print(f"RAG retrieval time: {processing_time} seconds")

        return retrieved_docs
