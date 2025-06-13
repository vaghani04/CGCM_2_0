from typing import Dict, List, Any, Optional
import json

from src.app.models.domain.graphdb_models import GraphQuery, GraphQueryResult
from src.app.services.neo4j_service import Neo4jService
from fastapi import Depends

class GraphDBQueryService:
    """Service to execute Cypher queries against the Neo4j database."""
    
    def __init__(self, neo4j_service: Neo4jService = Depends(Neo4jService)):
        self.neo4j_service = neo4j_service
    
    async def execute_cypher_query(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query against the Neo4j database.
        
        Args:
            cypher_query: The Cypher query string
            parameters: Dictionary of query parameters (optional)
            
        Returns:
            List of records returned by the query
        """
        if parameters is None:
            parameters = {}
        
        query = GraphQuery(cypher_query=cypher_query, parameters=parameters)
        
        try:
            result = await self.neo4j_service.execute_query(query)
            return result.records
        except Exception as e:
            print(f"Error executing Cypher query: {e}")
            return []
    
    async def get_function_info(self, function_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about functions matching the name."""
        cypher_query = """
            MATCH (f:Function)
            WHERE f.name CONTAINS $function_name
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(f)
            RETURN f.name as function_name, 
                   f.docstring as docstring,
                   f.parameters as parameters, 
                   f.return_type as return_type,
                   f.line_number as line_number,
                   file.path as file_path
            LIMIT $limit
        """
        parameters = {"function_name": function_name, "limit": limit}
        
        return await self.execute_cypher_query(cypher_query, parameters)
    
    async def get_function_usage(self, function_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about where a function is used/called."""
        cypher_query = """
            MATCH (caller:Function)-[:CALLS]->(callee:Function)
            WHERE callee.name CONTAINS $function_name
            MATCH (caller_file:File)-[:CONTAINS]->(caller)
            RETURN caller.name as caller_function,
                   caller_file.path as caller_file_path,
                   caller.line_number as caller_line_number,
                   callee.name as called_function
            LIMIT $limit
        """
        parameters = {"function_name": function_name, "limit": limit}
        
        return await self.execute_cypher_query(cypher_query, parameters)
    
    async def get_class_info(self, class_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about classes matching the name."""
        cypher_query = """
            MATCH (c:Class)
            WHERE c.name CONTAINS $class_name
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(c)
            OPTIONAL MATCH (c)-[:DEFINES]->(m:Method)
            RETURN c.name as class_name,
                   c.docstring as docstring,
                   file.path as file_path,
                   c.line_number as line_number,
                   collect(m.name) as methods
            LIMIT $limit
        """
        parameters = {"class_name": class_name, "limit": limit}
        
        return await self.execute_cypher_query(cypher_query, parameters)
    
    async def get_file_dependencies(self, file_path: str) -> List[Dict[str, Any]]:
        """Get dependencies of a file."""
        cypher_query = """
            MATCH (f:File {path: $file_path})-[:IMPORTS]->(dep:File)
            RETURN f.path as file_path,
                   collect(dep.path) as dependencies
        """
        parameters = {"file_path": file_path}
        
        return await self.execute_cypher_query(cypher_query, parameters)
    
    async def search_code_entities(self, keyword: str, entity_type: Optional[str] = None, 
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for code entities matching the keyword.
        
        Args:
            keyword: The search keyword
            entity_type: Optional entity type to filter by (Function, Class, File)
            limit: Maximum number of results to return
            
        Returns:
            List of matching entities
        """
        if entity_type == "Function":
            cypher_query = """
                MATCH (f:Function)
                WHERE f.name CONTAINS $keyword
                MATCH (file:File)-[:CONTAINS]->(f)
                RETURN f.name as name,
                       'Function' as entity_type,
                       file.path as file_path,
                       f.line_number as line_number,
                       f.docstring as docstring
                LIMIT $limit
            """
        elif entity_type == "Class":
            cypher_query = """
                MATCH (c:Class)
                WHERE c.name CONTAINS $keyword
                MATCH (file:File)-[:CONTAINS]->(c)
                RETURN c.name as name,
                       'Class' as entity_type,
                       file.path as file_path,
                       c.line_number as line_number,
                       c.docstring as docstring
                LIMIT $limit
            """
        elif entity_type == "File":
            cypher_query = """
                MATCH (f:File)
                WHERE f.path CONTAINS $keyword
                RETURN f.path as name,
                       'File' as entity_type,
                       f.path as file_path,
                       null as line_number,
                       f.docstring as docstring
                LIMIT $limit
            """
        else:
            # Search across all entity types
            cypher_query = """
                MATCH (n)
                WHERE (n:Function OR n:Class OR n:File)
                  AND (n.name CONTAINS $keyword OR n.path CONTAINS $keyword)
                OPTIONAL MATCH (file:File)-[:CONTAINS]->(n)
                WITH n, 
                     CASE 
                       WHEN n:Function THEN 'Function'
                       WHEN n:Class THEN 'Class'
                       WHEN n:File THEN 'File'
                       ELSE 'Unknown'
                     END as entity_type,
                     CASE 
                       WHEN n:File THEN n.path
                       ELSE file.path
                     END as file_path
                RETURN CASE 
                         WHEN n:File THEN n.path
                         ELSE n.name
                       END as name,
                       entity_type,
                       file_path,
                       n.line_number as line_number,
                       n.docstring as docstring
                LIMIT $limit
            """
        
        parameters = {"keyword": keyword, "limit": limit}
        
        return await self.execute_cypher_query(cypher_query, parameters)
    
    async def process_structured_result(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process the query results into a structured format.
        
        Args:
            records: List of records returned by the query
            
        Returns:
            Structured dictionary with the processed results
        """
        if not records:
            return {"results": [], "count": 0, "found": False}
        
        # Process any special data formats
        processed_records = []
        for record in records:
            processed_record = {}
            for key, value in record.items():
                # Handle JSON strings that might be stored in the database
                if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                    try:
                        processed_record[key] = json.loads(value)
                    except json.JSONDecodeError:
                        processed_record[key] = value
                else:
                    processed_record[key] = value
            processed_records.append(processed_record)
        
        return {
            "results": processed_records,
            "count": len(processed_records),
            "found": len(processed_records) > 0
        } 