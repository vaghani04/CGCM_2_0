from typing import Dict, List, Any, Optional

class CypherQueryService:
    """Service to generate Neo4j Cypher queries based on the analyzed user query."""
    
    def __init__(self):
        # Templates for different query types
        self.query_templates = {
            # Find information about a specific function
            "function_info": """
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
            """,
            
            # Find where a function is used/called
            "function_usage": """
                MATCH (caller:Function)-[:CALLS]->(callee:Function)
                WHERE callee.name CONTAINS $function_name
                MATCH (caller_file:File)-[:CONTAINS]->(caller)
                RETURN caller.name as caller_function,
                       caller_file.path as caller_file_path,
                       caller.line_number as caller_line_number,
                       callee.name as called_function
                LIMIT $limit
            """,
            
            # Find information about a class
            "class_info": """
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
            """,
            
            # Find file dependencies
            "file_dependencies": """
                MATCH (f:File {path: $file_path})-[:IMPORTS]->(dep:File)
                RETURN f.path as file_path,
                       collect(dep.path) as dependencies
            """,
            
            # Find imported files
            "file_imports": """
                MATCH (f:File)-[:IMPORTS]->(imp:File)
                WHERE imp.path CONTAINS $import_path
                RETURN f.path as file_path,
                       imp.path as imported_file
                LIMIT $limit
            """,
            
            # Find implementations of a class/interface
            "class_implementations": """
                MATCH (c:Class)-[:INHERITS_FROM]->(parent:Class)
                WHERE parent.name CONTAINS $class_name
                MATCH (file:File)-[:CONTAINS]->(c)
                RETURN c.name as class_name,
                       file.path as file_path,
                       c.docstring as docstring
                LIMIT $limit
            """,
            
            # Generic search for files containing keyword
            "file_search": """
                MATCH (f:File)
                WHERE f.path CONTAINS $keyword
                RETURN f.path as file_path,
                       f.language as language,
                       f.lines_of_code as lines_of_code
                LIMIT $limit
            """,
            
            # Search for functions by name pattern
            "function_search": """
                MATCH (f:Function)
                WHERE f.name CONTAINS $keyword
                MATCH (file:File)-[:CONTAINS]->(f)
                RETURN f.name as function_name,
                       file.path as file_path,
                       f.line_number as line_number,
                       f.docstring as docstring
                LIMIT $limit
            """
        }
    
    async def generate_query(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Cypher query based on the analyzed user query.
        
        Args:
            analysis: Dictionary with query analysis results
            
        Returns:
            Dictionary containing Cypher query and parameters
        """
        intent = analysis.get("intent", "information")
        entities = analysis.get("entities", {})
        constraints = analysis.get("constraints", {})
        raw_query = analysis.get("raw_query", "")
        
        # Set default limit
        limit = constraints.get("limit", 10)
        if limit is None:
            limit = 100  # Use a reasonable upper bound if no limit specified
        
        # Determine which query template to use
        template_key, parameters = self._select_query_template(intent, entities, raw_query)
        
        # Add limit to parameters
        parameters["limit"] = limit
        
        # Get the query template
        cypher_query = self.query_templates.get(template_key)
        
        if not cypher_query:
            # Fallback to a generic search if no specific template matches
            cypher_query = self.query_templates["function_search"]
            # Extract a potential keyword from the raw query
            keywords = raw_query.split()
            keyword = next((word for word in keywords if len(word) > 3 and word.isalnum()), "")
            parameters = {"keyword": keyword, "limit": limit}
        
        return {
            "cypher_query": cypher_query,
            "parameters": parameters,
            "template_used": template_key
        }
    
    def _select_query_template(self, intent: str, entities: Dict[str, List[str]], 
                               raw_query: str) -> tuple[str, Dict[str, Any]]:
        """
        Select an appropriate query template based on intent and entities.
        
        Args:
            intent: The query intent
            entities: Extracted entities from the query
            raw_query: The raw user query
            
        Returns:
            Tuple of (template_key, parameters)
        """
        # Initialize parameters
        parameters = {}
        
        # Function-related queries
        if entities.get("function") and intent in ["information", "implementation"]:
            function_name = entities["function"][0]
            parameters["function_name"] = function_name
            return "function_info", parameters
            
        elif entities.get("function") and intent == "usage":
            function_name = entities["function"][0]
            parameters["function_name"] = function_name
            return "function_usage", parameters
            
        # Class-related queries
        elif entities.get("class") and intent in ["information", "implementation"]:
            class_name = entities["class"][0]
            parameters["class_name"] = class_name
            return "class_info", parameters
            
        elif entities.get("class") and intent == "inheritance":
            class_name = entities["class"][0]
            parameters["class_name"] = class_name
            return "class_implementations", parameters
            
        # File-related queries
        elif entities.get("file") and intent == "dependency":
            file_path = entities["file"][0]
            parameters["file_path"] = file_path
            return "file_dependencies", parameters
            
        elif "imports" in raw_query or "import" in raw_query:
            # Try to extract import path from query
            for word in raw_query.split():
                if "." in word:
                    parameters["import_path"] = word
                    break
            if "import_path" not in parameters:
                # If no specific import mentioned, use a generic term
                parameters["import_path"] = ""
            return "file_imports", parameters
            
        # Generic searches
        elif intent == "search" or "find" in raw_query:
            # Extract keyword from raw query
            words = raw_query.split()
            for i, word in enumerate(words):
                if word in ["find", "search", "about", "for"] and i < len(words) - 1:
                    keyword = words[i+1].strip(",.?!;:'\"")
                    if len(keyword) > 2:
                        parameters["keyword"] = keyword
                        break
            
            if "keyword" not in parameters:
                # Use first non-trivial word as fallback
                for word in words:
                    if len(word) > 3 and word not in ["find", "search", "about", "what", "where", "which"]:
                        parameters["keyword"] = word
                        break
                else:
                    parameters["keyword"] = ""
            
            # Determine if searching for functions or files
            if "function" in raw_query or "method" in raw_query:
                return "function_search", parameters
            else:
                return "file_search", parameters
                
        # Default fallback
        else:
            # Extract a potential keyword from the raw query
            words = raw_query.split()
            for word in words:
                if len(word) > 3 and word.isalnum():
                    parameters["keyword"] = word
                    break
            else:
                parameters["keyword"] = ""
                
            return "function_search", parameters 