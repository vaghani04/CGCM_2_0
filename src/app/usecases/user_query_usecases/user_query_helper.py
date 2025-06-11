import json
import os
from fastapi import Depends
from src.app.services.context_assembly_service import ContextAssemblyService
from src.app.usecases.user_query_usecases.repo_map_usecase import RepoMapUsecase
from src.app.usecases.user_query_usecases.rag_retrieval_usecase import RAGRetrievalUsecase
from typing import Dict, Any
from src.app.utils.hash_calculator import calculate_special_hash, calculate_hash
from src.app.usecases.context_gather_usecases.context_gather_helper import ContextGatherHelper
from src.app.usecases.user_query_usecases.grep_search_usecase import GrepSearchUsecase
from src.app.models.schemas.grep_search_query_schema import GrepSearchQueryRequest

class UserQueryHelper:
    def __init__(self,
                context_assembly_service: ContextAssemblyService = Depends(ContextAssemblyService),
                repo_map_usecase: RepoMapUsecase = Depends(RepoMapUsecase),
                rag_retrieval_usecase: RAGRetrievalUsecase = Depends(RAGRetrievalUsecase),
                context_gather_helper: ContextGatherHelper = Depends(ContextGatherHelper),
                grep_search_usecase: GrepSearchUsecase = Depends(GrepSearchUsecase),
    ):
        self.context_assembly_service = context_assembly_service
        self.repo_map_usecase = repo_map_usecase
        self.rag_retrieval_usecase = rag_retrieval_usecase
        self.context_gather_helper = context_gather_helper
        self.grep_search_usecase = grep_search_usecase
        
    async def context_from_rag(self, user_query_data: Dict[str, Any]) -> str:
        query = user_query_data["query"]
        codebase_path = user_query_data["codebase_path"]
        target_directories = user_query_data.get("target_directories", [])
        current_git_branch = await self.context_gather_helper.get_current_branch_name(codebase_path)
        codebase_path_special_hash = calculate_special_hash(codebase_path)
        codebase_path_hash = calculate_hash(codebase_path)
        codebase_dir_path = codebase_path.split('/')[-1]
        index_name = f"{codebase_dir_path.replace('_', '-')}-{codebase_path_special_hash}"

        context = await self.rag_retrieval_usecase.rag_retrieval(query, index_name, target_directories, current_git_branch, codebase_path_hash)
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
            query = user_query_data["query"]
            codebase_path = user_query_data["codebase_path"]

            # graph_db_project_structure = await self.repo_map_usecase._get_project_structure()
            # # return graph_db_project_structure
            # with open("intermediate_outputs/graph_db_project_structure.txt", "w") as f:
            #     f.write(graph_db_project_structure)
            
            # Get project structure
            print(f"Getting directory structure for {codebase_path}")
            project_structure = await self.repo_map_usecase.get_directory_structure(codebase_path, depth=3)
            
            # Generate Cypher queries using LLM
            print(f"Generating Cypher queries for: {query}")
            cypher_queries = await self.repo_map_usecase._generate_cypher_queries(query, project_structure)

            # with open("intermediate_outputs/cypher_queries.json", "r") as f:
            #     cypher_queries = json.load(f)
            #     cypher_queries = cypher_queries["queries"]
            # Execute queries in parallel
            print(f"Executing {len(cypher_queries)} Cypher queries")
            
            results = await self.repo_map_usecase._execute_queries_parallel(cypher_queries)
            with open("intermediate_outputs/cypher_queries_execution_results.json", "w") as f:
                json.dump(results, f)

            
            # with open("intermediate_outputs/cypher_queries_execution_results.json", "r") as f:
            #     results = json.load(f)
            
            
            # Assemble the final context
            print(f"Assembling context from {len(results.get('results', []))} results")
            context = await self.context_assembly_service.assemble_context(results, query)
            
            
            with open("intermediate_outputs/repo_map_context.txt", "w") as f:
                f.write(context)

            return context
            
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            print(error_message)
            return f"Failed to retrieve context from repository map. Error: {str(e)}"
        
    async def context_from_grep_search(self, user_query_data: Dict[str, Any]) -> str:

        result = await self.grep_search_usecase.execute(user_query_data)
        return result
