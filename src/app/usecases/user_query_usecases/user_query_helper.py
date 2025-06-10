from fastapi import Depends
from src.app.services.query_analysis_service import QueryAnalysisService
from src.app.services.cypher_query_service import CypherQueryService
from src.app.services.graphdb_query_service import GraphDBQueryService
from src.app.services.context_assembly_service import ContextAssemblyService
from typing import Dict, List, Any

class UserQueryHelper:
    def __init__(self,
                 query_analysis_service: QueryAnalysisService = Depends(QueryAnalysisService),
                 cypher_query_service: CypherQueryService = Depends(CypherQueryService),
                 graphdb_query_service: GraphDBQueryService = Depends(GraphDBQueryService),
                 context_assembly_service: ContextAssemblyService = Depends(ContextAssemblyService)):
        self.query_analysis_service = query_analysis_service
        self.cypher_query_service = cypher_query_service
        self.graphdb_query_service = graphdb_query_service
        self.context_assembly_service = context_assembly_service

    async def context_from_repo_map(self, query: str) -> str:
        """
        Process a natural language query and retrieve relevant context from the repository map in GraphDB.
        
        Args:
            query: The natural language query string
            
        Returns:
            Context assembled from the GraphDB query results
        """
        try:
            # Step 1: Analyze the natural language query
            query_analysis = await self.query_analysis_service.analyze_query(query)
            
            # Step 2: Generate appropriate Cypher query
            cypher_query_data = await self.cypher_query_service.generate_query(query_analysis)
            
            # Step 3: Execute the Cypher query against the GraphDB
            cypher_query = cypher_query_data["cypher_query"]
            parameters = cypher_query_data["parameters"]
            template_used = cypher_query_data["template_used"]
            
            query_results = await self.graphdb_query_service.execute_cypher_query(cypher_query, parameters)
            
            # Step 4: Process the results into a structured format
            structured_results = await self.graphdb_query_service.process_structured_result(query_results)
            structured_results["template_used"] = template_used
            
            # Step 5: Assemble the final context
            context = await self.context_assembly_service.assemble_context(structured_results, query)
            
            return context
            
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            print(error_message)
            return f"Failed to retrieve context from repository map. Error: {str(e)}"