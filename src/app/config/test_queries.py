# Define cypher queries for different aspects of NL context extraction
NL_CONTEXT_QUERIES = [
    {
        "name": "functions_with_docstrings",
        "query": """
            MATCH (f:Function)
            WHERE f.docstring IS NOT NULL AND f.docstring <> ''
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(f)
            RETURN f.name as function_name, 
                    f.docstring as docstring,
                    f.parameters as parameters,
                    f.return_type as return_type,
                    file.path as file_path,
                    f.line_number as line_number
            ORDER BY f.name
            LIMIT 15
        """,
        "parameters": {}
    },
    {
        "name": "classes_with_docstrings",
        "query": """
            MATCH (c:Class)
            WHERE c.docstring IS NOT NULL AND c.docstring <> ''
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(c)
            RETURN c.name as class_name,
                    c.docstring as docstring,
                    c.bases as bases,
                    file.path as file_path,
                    c.line_number as line_number,
                    c.method_count as method_count
            ORDER BY c.name
            LIMIT 15
        """,
        "parameters": {}
    },
    {
        "name": "most_used_functions",
        "query": """
            MATCH (caller:Function)-[r:CALLS]->(callee:Function)
            WITH callee, count(r) as usage_count
            WHERE usage_count > 1
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(callee)
            RETURN callee.name as function_name,
                    callee.docstring as docstring,
                    callee.parameters as parameters,
                    file.path as file_path,
                    usage_count
            ORDER BY usage_count DESC
            LIMIT 15
        """,
        "parameters": {}
    },
    {
        "name": "files_with_docstrings",
        "query": """
            MATCH (f:File)
            WHERE f.docstring IS NOT NULL AND f.docstring <> ''
            RETURN f.path as file_path,
                    f.docstring as docstring,
                    f.language as language,
                    f.lines_of_code as lines_of_code
            ORDER BY f.path
            LIMIT 15
        """,
        "parameters": {}
    },
    {
        "name": "business_logic_functions",
        "query": """
            MATCH (f:Function)
            WHERE f.name CONTAINS 'create' OR 
                    f.name CONTAINS 'update' OR 
                    f.name CONTAINS 'delete' OR 
                    f.name CONTAINS 'get' OR 
                    f.name CONTAINS 'process' OR 
                    f.name CONTAINS 'handle' OR 
                    f.name CONTAINS 'validate' OR 
                    f.name CONTAINS 'generate'
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(f)
            RETURN f.name as function_name,
                    f.docstring as docstring,
                    f.parameters as parameters,
                    file.path as file_path,
                    f.line_number as line_number
            ORDER BY f.name
            LIMIT 15
        """,
        "parameters": {}
    },
    {
        "name": "function_signatures_by_usage",
        "query": """
            MATCH (caller:Function)-[r:CALLS]->(callee:Function)
            WITH callee, count(r) as usage_count
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(callee)
            RETURN callee.name as function_name,
                    callee.parameters as parameters,
                    callee.return_type as return_type,
                    callee.docstring as docstring,
                    file.path as file_path,
                    usage_count
            ORDER BY usage_count DESC, callee.name ASC
            LIMIT 15
        """,
        "parameters": {}
    },
    {
        "name": "class_method_signatures",
        "query": """
            MATCH (c:Class)-[:DEFINES]->(m:Function)
            WHERE m.is_method = true
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(c)
            RETURN c.name as class_name,
                    m.name as method_name,
                    m.parameters as parameters,
                    m.return_type as return_type,
                    m.docstring as method_docstring,
                    c.docstring as class_docstring,
                    file.path as file_path
            ORDER BY c.name, m.name
            LIMIT 15
        """,
        "parameters": {}
    }
]