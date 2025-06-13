import asyncio
import json
import time

from fastapi import Depends

from src.app.config.settings import settings
from src.app.prompts.rag_search_query_making_prompts import (
    IS_RAG_SEARCH_REQUIRED_SYSTEM_PROMPT,
    IS_RAG_SEARCH_REQUIRED_USER_PROMPT,
)
from src.app.repositories.chunking_repository import ChunkingRepository
from src.app.services.embedding_service import EmbeddingService
from src.app.services.openai_service import OpenAIService
from src.app.services.pinecone_service import PineconeService
from src.app.services.re_ranking_service import RerankerService
from src.app.utils.codebase_overview_utils import get_directory_structure
from src.app.utils.logging_util import loggers
from src.app.utils.response_parser import parse_response


class RAGRetrievalUsecase:
    def __init__(
        self,
        embedding_service: EmbeddingService = Depends(EmbeddingService),
        pinecone_service: PineconeService = Depends(PineconeService),
        reranker_service: RerankerService = Depends(RerankerService),
        chunking_repository: ChunkingRepository = Depends(ChunkingRepository),
        openai_service: OpenAIService = Depends(OpenAIService),
    ):
        self.embedding_service = embedding_service
        self.pinecone_service = pinecone_service
        self.reranker_service = reranker_service
        self.embedding_model = settings.VOYAGEAI_EMBEDDINGS_MODEL
        self.reranker_model = settings.VOYAGEAI_RERANKING_MODEL
        self.similarity_metric = settings.INDEXING_SIMILARITY_METRIC
        self.dimension = settings.EMBEDDINGS_DIMENSION
        self.query_input_type = "query"
        self.top_k = settings.RAG_TOP_K
        self.top_n = settings.RAG_TOP_N
        self.chunking_repository = chunking_repository
        self.openai_service = openai_service

    async def fetch_docs_from_mongodb(
        self,
        doc_metadata: list[dict],
        current_git_branch: str,
        codebase_path_hash: str,
    ):
        tasks = []
        for doc in doc_metadata:
            file_path = doc.get("file_path")
            start_line = doc.get("start_line")
            task = (
                self.chunking_repository.get_chunk_content_by_fp_sl_git_branch(
                    file_path,
                    start_line,
                    current_git_branch,
                    codebase_path_hash,
                )
            )
            tasks.append(task)

        chunks = await asyncio.gather(*tasks)
        documents = [chunk for chunk in chunks if chunk]
        return documents

    async def perform_rag(
        self,
        query: str,
        index_name: str,
        target_directories: list[str],
        current_git_branch: str,
        codebase_path_hash: str,
    ):

        # Step-1: Query embeddings generation
        query_embedding = (
            await self.embedding_service.voyageai_dense_embeddings(
                self.embedding_model,
                dimension=self.dimension,
                inputs=[query],
                input_type=self.query_input_type,
            )
        )
        query_embedding = query_embedding[0]
        # query_embedding = [random.random() for _ in range(self.dimension)]

        # Step-2: pinecone query
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
            namespace=current_git_branch,
        )

        if not vector_search_results or not vector_search_results.get(
            "matches"
        ):
            return []

        # Step-3: extract metadata
        doc_metadata = []
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
                    }
                )
        with open(
            "intermediate_outputs/rag_search_outputs/pinecone_retrieval_results.json",
            "w",
        ) as f:
            json.dump(doc_metadata, f, indent=2)

        # Step-4: Fetch from mongodb actual data
        documents = await self.fetch_docs_from_mongodb(
            doc_metadata, current_git_branch, codebase_path_hash
        )

        if not documents:
            return []

        with open(
            "intermediate_outputs/rag_search_outputs/documents_fetched_from_mongodb.json",
            "w",
        ) as f:
            json.dump(documents, f, indent=2)

        reranked_results = await self.reranker_service.voyage_rerank(
            self.reranker_model, query, documents, self.top_n
        )

        # Step-5: reranker
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

        # Step-6: save results
        full_final_results = final_results
        with open(
            "intermediate_outputs/rag_search_outputs/rag_retrieval_results.json",
            "w",
        ) as f:
            json.dump(full_final_results, f, indent=2)
        return full_final_results

    async def rag_retrieval(
        self,
        query: str,
        index_name: str,
        target_directories: list[str] = [],
        current_git_branch: str = "default",
        codebase_path_hash: str = "",
        codebase_path: str = "",
    ):

        rag_required = await self.is_rag_required(query, codebase_path)

        if not rag_required:
            return [
                {
                    "text": "No RAG required",
                    "relevance_score": 0,
                    "metadata": {
                        "reason": "Query does not contain specific technical content suitable for RAG retrieval"
                    },
                }
            ]

        start_time = time.time()

        try:
            retrieved_docs = await self.perform_rag(
                query,
                index_name,
                target_directories,
                current_git_branch,
                codebase_path_hash,
            )

            filtered_results = await self.filter_results(retrieved_docs)

            end_time = time.time()
            processing_time = end_time - start_time

            print(f"✓ RAG retrieval completed")
            print(f"Total RAG retrieval time: {processing_time:.2f} seconds")

            return filtered_results

        except Exception as e:
            loggers["main"].error(f"Error during RAG execution: {e}")
            end_time = time.time()
            processing_time = end_time - start_time
            loggers["main"].info(
                f"Processing time before error: {processing_time:.2f} seconds"
            )
            raise e

    async def filter_results(self, retrieved_docs: list[dict]):
        filtered_results = []
        for doc in retrieved_docs:
            if doc.get("relevance_score") > 0.5:
                filtered_doc = doc.copy()
                if "metadata" in filtered_doc and isinstance(
                    filtered_doc["metadata"], dict
                ):
                    metadata_copy = filtered_doc["metadata"].copy()
                    metadata_copy.pop(
                        "score", None
                    )  # Remove score if it exists
                    filtered_doc["metadata"] = metadata_copy
                filtered_results.append(filtered_doc)

        with open(
            "intermediate_outputs/rag_search_outputs/filtered_rag_results.json",
            "w",
        ) as f:
            json.dump(filtered_results, f, indent=2)
        return filtered_results

    async def is_rag_required(self, query: str, codebase_path: str):

        directory_structure = await get_directory_structure(
            codebase_path, depth=5
        )
        with open(
            "intermediate_outputs/rag_search_outputs/directory_structure.txt",
            "w",
        ) as f:
            f.write(directory_structure)

        user_prompt = IS_RAG_SEARCH_REQUIRED_USER_PROMPT.format(
            user_query=query, directory_structure=directory_structure
        )

        response = await self.openai_service.completions(
            system_prompt=IS_RAG_SEARCH_REQUIRED_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        parsed_response = parse_response(response)
        with open(
            "intermediate_outputs/rag_search_outputs/rag_decision_llm_response.json",
            "w",
        ) as f:
            json.dump(parsed_response, f, indent=2)

        rag_required = parsed_response.get("rag_required", False)

        return rag_required
