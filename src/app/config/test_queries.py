"""
Sample test queries for the GraphDB query system.
These queries can be used to test the system's ability to analyze queries,
generate Cypher queries, and retrieve relevant context.
"""

# Example natural language queries
TEST_QUERIES = [
    # Function-related queries
    "How does the context_from_repo_map function work?",
    "What parameters does the execute_cypher_query function take?",
    "Who uses the analyze_query function?",
    "Find all functions that use Neo4j",
    
    # Class-related queries
    "What is the UserQueryHelper class?",
    "Show me the methods in the Neo4jService class",
    "Which classes implement the GraphNode interface?",
    
    # File-related queries
    "What files import neo4j?",
    "Show dependencies of user_query_helper.py",
    "Find all Python files in the services directory",
    
    # General search queries
    "Find code related to context gathering",
    "Show me the GraphDB schema definition",
    "Where is the repository map stored?",
    "How are Cypher queries generated from natural language?"
]

# Expected Cypher queries for each test query
EXPECTED_CYPHER_QUERIES = {
    "How does the context_from_repo_map function work?": {
        "template": "function_info",
        "parameters": {"function_name": "context_from_repo_map"}
    },
    "What parameters does the execute_cypher_query function take?": {
        "template": "function_info",
        "parameters": {"function_name": "execute_cypher_query"}
    },
    "Who uses the analyze_query function?": {
        "template": "function_usage",
        "parameters": {"function_name": "analyze_query"}
    },
    "What is the UserQueryHelper class?": {
        "template": "class_info",
        "parameters": {"class_name": "UserQueryHelper"}
    },
    "What files import neo4j?": {
        "template": "file_imports",
        "parameters": {"import_path": "neo4j"}
    },
    "Show dependencies of user_query_helper.py": {
        "template": "file_dependencies",
        "parameters": {"file_path": "src/app/usecases/user_query_usecases/user_query_helper.py"}
    }
} 