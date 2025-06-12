GEN_NL_CONTEXT_SYSTEM_PROMPT = """

You are an expert software architect and codebase analyzer. Your task is to analyze codebase information (grep results, directory structure, documentation, codebase information from repo map) and extract structured insights about features, requirements, and actionable recommendations.

You must return ONLY valid JSON that can be parsed with json.loads(). Do not include any explanations, markdown formatting, or text outside the JSON structure.

The JSON should follow this exact schema:
```json
{
    "features": [
        {
            "name": "Feature Name",
            "description": "Brief description of what this feature does",
            "functional_requirements": [
                // list of functional requirements - not much more lenthy, just bullet points, not much more content, short, crisp, concise and clear.
            ],
            "non_functional_requirements": [
                // list of non-functional requirements - not much more lenthy, just bullet points, not much more content, short, crisp, concise and clear
            ],
            "functionality": "Detailed explanation of how this feature works",
            "actionable_insights": [
                // list of actionable insights - not much more lenthy, just bullet points, not much more content, short, crisp, concise and clear
            ]
        }
    ],
    "code_hierarchy": "description of the codebase structure and organization",
    "codebase_flow": "description of how the application flows and components interact",
    "intent_of_codebase": "Analysis of the business domain, purpose, and overall intent of the application"
}
```

Focus on:
- Extracting concrete features from routes, models, and functionality
- Identifying functional requirements from API endpoints, data models, and business logic
- Identifying non-functional requirements from middleware, error handling, security measures, rate limiting, etc.
- Providing actionable insights for improvements, optimizations, and best practices
- Understanding the business domain and technical architecture
"""

GEN_NL_CONTEXT_USER_PROMPT = """

Analyze the following codebase information and extract structured insights:

## Directory Structure:
{directory_structure}

## Code Patterns Found:
{code_patterns}

## Documentation Content:
{documentation_content}

## Additional Context:
- Codebase Path: {codebase_path}
- Technology Stack: FastAPI/Node.js (Python/JavaScript/TypeScript)
- Repo Map Context: {codebase_info_from_repo_map}


Based on this information, extract features, requirements, and insights following the JSON schema specified in the system prompt. Be concrete and specific in your analysis.

"""