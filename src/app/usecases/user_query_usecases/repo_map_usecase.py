from typing import List, Dict, Any
import json
import asyncio
from fastapi import Depends
from src.app.prompts.cypher_query_making_prompt import CYPHER_QUERY_MAKING_USER_PROMPT, CYPHER_QUERY_MAKING_SYSTEM_PROMPT
from src.app.services.openai_service import OpenAIService
from src.app.services.graphdb_query_service import GraphDBQueryService
from src.app.utils.response_parser import parse_response

class RepoMapUsecase:
    def __init__(self,
                 graphdb_query_service: GraphDBQueryService = Depends(GraphDBQueryService),
                 openai_service: OpenAIService = Depends(OpenAIService)):
        self.graphdb_query_service = graphdb_query_service
        self.openai_service = openai_service
        
    async def _get_project_structure(self) -> str:
        """
        Get a simplified representation of the project structure.
        This could be enhanced to provide more detailed structure information.
        """
        try:
            # Query database for high-level structure
            node_count_query = "MATCH (n) RETURN labels(n) as type, count(n) as count"
            relationship_count_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
            
            node_counts = await self.graphdb_query_service.execute_cypher_query(node_count_query, {})
            rel_counts = await self.graphdb_query_service.execute_cypher_query(relationship_count_query, {})
            
            # Format as a simple string
            structure_parts = ["Database structure:"]
            
            structure_parts.append("Node types:")
            for node_type in node_counts:
                structure_parts.append(f"- {node_type['type']}: {node_type['count']}")
                
            structure_parts.append("Relationship types:")
            for rel_type in rel_counts:
                structure_parts.append(f"- {rel_type['type']}: {rel_type['count']}")
                
            return "\n".join(structure_parts)
        except Exception as e:
            print(f"Error getting project structure: {e}")
            return "Project structure information unavailable."


    async def _generate_cypher_queries(self, query: str, directory_structure: str) -> List[Dict[str, Any]]:
        """
        Generate Cypher queries using LLM.
        
        Args:
            query: The user's natural language query
            directory_structure: String representation of the directory structure
            
        Returns:
            List of query objects with query string and description
        """
        # Format the user prompt with the query and project structure
        user_prompt = CYPHER_QUERY_MAKING_USER_PROMPT.format(
            query=query,
            directory_structure=directory_structure
        )
        
        # Call the OpenAI service
        response = await self.openai_service.completions(
            system_prompt=CYPHER_QUERY_MAKING_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        # Parse the response to extract the queries
        parsed_response = parse_response(response)
        
        # Save the parsed response for debugging
        with open("intermediate_outputs/repo_map_search_outputs/cypher_queries.json", "w") as f:
            json.dump(parsed_response, f, indent=2)
        
        # Validate the parsed response
        if not isinstance(parsed_response, dict):
            print(f"Warning: Expected dict response, got {type(parsed_response)}")
            return []
        
        # Extract queries from the response
        queries = parsed_response.get("queries", [])
        
        # If queries is just a list of strings, convert to list of dicts
        formatted_queries = []
        for i, query_item in enumerate(queries):
            if isinstance(query_item, str):
                # Simple string query
                formatted_queries.append({
                    "query": query_item,
                    "description": f"Query {i+1}"
                })
            elif isinstance(query_item, dict):
                # Already formatted as a dict with query and description
                cypher_query = query_item.get("query", "")
                description = query_item.get("description", f"Query {i+1}")
                
                if cypher_query:
                    formatted_queries.append({
                        "query": cypher_query,
                        "description": description
                    })
        
        return formatted_queries
        
    
    async def _execute_queries_parallel(self, queries: List[str]) -> Dict[str, Any]:
        """
        Execute multiple Cypher queries in parallel and aggregate the results.
        
        Args:
            queries: List of Cypher queries to execute
            
        Returns:
            Aggregated results from all queries
        """
        tasks = []
        for i, query in enumerate(queries):
            description = f"Query {i+1}"
            if isinstance(query, dict):
                cypher_query = query.get("query", "")
                description = query.get("description", description)
            else:
                cypher_query = query
                
            if not cypher_query.strip():
                continue
                
            task = asyncio.create_task(
                self.graphdb_query_service.execute_cypher_query(cypher_query)
            )
            tasks.append((task, description))
        
        # Wait for all tasks to complete
        all_results = []
        for task, description in tasks:
            try:
                result = await task
                # Add query description to each result item
                for item in result:
                    item["description"] = description
                all_results.extend(result)
            except Exception as e:
                print(f"Error executing query: {e}")
        
        return all_results