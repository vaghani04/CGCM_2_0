from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class QueryAnalysisResult:
    """Result of analyzing a natural language query."""
    raw_query: str
    entities: Dict[str, List[str]] = field(default_factory=dict)
    intent: str = "information"
    constraints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CypherQueryResult:
    """Result of generating a Cypher query."""
    cypher_query: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    template_used: str = "generic"

@dataclass
class CodeEntityReference:
    """Reference to a code entity in the codebase."""
    name: str
    entity_type: str  # Function, Class, File, etc.
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    docstring: Optional[str] = None
    
@dataclass
class CodeSnippet:
    """Code snippet from a file."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    highlight_line: Optional[int] = None
    entity_name: Optional[str] = None

@dataclass
class StructuredQueryResult:
    """Structured result of a repository query."""
    entities: List[CodeEntityReference] = field(default_factory=list)
    snippets: List[CodeSnippet] = field(default_factory=list)
    found: bool = False
    count: int = 0
    template_used: str = "generic"
    raw_results: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class RepoQueryContext:
    """Final context assembled from repository query."""
    context: str
    query: str
    structured_result: Optional[StructuredQueryResult] = None
    error: Optional[str] = None 