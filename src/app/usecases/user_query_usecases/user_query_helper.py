import json
from fastapi import Depends
from src.app.usecases.user_query_usecases.repo_map_usecase import RepoMapUsecase
from src.app.usecases.user_query_usecases.rag_retrieval_usecase import RAGRetrievalUsecase
from typing import Dict, Any
from src.app.utils.hash_calculator import calculate_special_hash, calculate_hash
from src.app.usecases.context_gather_usecases.context_gather_helper import ContextGatherHelper
from src.app.usecases.user_query_usecases.grep_search_usecase import GrepSearchUsecase
from src.app.usecases.user_query_usecases.nl_search_usecase import NLSearchUsecase
from src.app.utils.codebase_overview_utils import get_directory_structure
from src.app.utils.logging_util import loggers
import time
class UserQueryHelper:
    def __init__(self,
                repo_map_usecase: RepoMapUsecase = Depends(RepoMapUsecase),
                rag_retrieval_usecase: RAGRetrievalUsecase = Depends(RAGRetrievalUsecase),
                context_gather_helper: ContextGatherHelper = Depends(ContextGatherHelper),
                grep_search_usecase: GrepSearchUsecase = Depends(GrepSearchUsecase),
                nl_search_usecase: NLSearchUsecase = Depends(NLSearchUsecase),
    ):
        self.repo_map_usecase = repo_map_usecase
        self.rag_retrieval_usecase = rag_retrieval_usecase
        self.context_gather_helper = context_gather_helper
        self.grep_search_usecase = grep_search_usecase
        self.nl_search_usecase = nl_search_usecase
    async def context_from_nl_insights(self, user_query_data: Dict[str, Any]) -> str:
        start_time = time.time()
        current_git_branch = await self.context_gather_helper.get_current_branch_name(user_query_data["codebase_path"])
        user_query_data["current_git_branch"] = current_git_branch

        nl_context = await self.nl_search_usecase.nl_search(user_query_data)
        end_time = time.time()
        processing_time = end_time - start_time
        loggers["time_tracker"].info(f"Processing time for NL context: {processing_time:.2f} seconds")
        return nl_context

    async def context_from_rag(self, user_query_data: Dict[str, Any]) -> str:
        start_time = time.time()
        query = user_query_data["query"]
        codebase_path = user_query_data["codebase_path"]
        target_directories = user_query_data.get("target_directories", [])
        current_git_branch = await self.context_gather_helper.get_current_branch_name(codebase_path)
        codebase_path_special_hash = calculate_special_hash(codebase_path)
        codebase_path_hash = calculate_hash(codebase_path)
        codebase_dir_path = codebase_path.split('/')[-1]
        index_name = f"{codebase_dir_path.lower().replace('_', '-')}-{codebase_path_special_hash}"

        context = await self.rag_retrieval_usecase.rag_retrieval(query, index_name, target_directories, current_git_branch, codebase_path_hash, codebase_path)
        end_time = time.time()
        processing_time = end_time - start_time
        loggers["time_tracker"].info(f"Processing time for RAG context: {processing_time:.2f} seconds")
        return context


    async def context_from_repo_map(self, user_query_data: Dict[str, Any]) -> str:
        """
        Process a natural language query and retrieve relevant context from the repository map in GraphDB.
        Using LLM to generate Cypher queries directly from user input.
        
        Args:
            user_query_data: Dictionary containing 'query' and 'codebase_path' keys
            
        Returns:
            Context assembled from the GraphDB query results
        """
        try:
            start_time = time.time()
            query = user_query_data["query"]
            codebase_path = user_query_data["codebase_path"]

            directory_structure = await get_directory_structure(codebase_path, depth=5)

            with open("intermediate_outputs/repo_map_search_outputs/directory_structure.txt", "w") as f:
                f.write(directory_structure)

            cypher_queries = await self.repo_map_usecase._generate_cypher_queries(query, directory_structure)

            # Execute queries in parallel
            loggers["main"].info(f"Executing {len(cypher_queries)} Cypher queries")
            
            results = await self.repo_map_usecase._execute_queries_parallel(cypher_queries)
            with open("intermediate_outputs/repo_map_search_outputs/cypher_queries_execution_results.json", "w") as f:
                json.dump(results, f)

            formatted_results = await self.repo_map_usecase.format_results(results)
            with open("intermediate_outputs/repo_map_search_outputs/formatted_results.json", "w") as f:
                json.dump(formatted_results, f)

            end_time = time.time()
            processing_time = end_time - start_time
            loggers["time_tracker"].info(f"Processing time for repo map context: {processing_time:.2f} seconds")

            return formatted_results
            
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            loggers["main"].error(error_message)
            return f"Failed to retrieve context from repository map. Error: {str(e)}"
        
    async def context_from_grep_search(self, user_query_data: Dict[str, Any]) -> str:
        start_time = time.time()
        result = await self.grep_search_usecase.execute(user_query_data)
        end_time = time.time()
        processing_time = end_time - start_time
        loggers["time_tracker"].info(f"Processing time for grep search context: {processing_time:.2f} seconds")
        return result
