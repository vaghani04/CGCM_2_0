from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(Enum):
    """Types of nodes in the graph database."""

    FILE = "File"
    DIRECTORY = "Directory"
    FUNCTION = "Function"
    CLASS = "Class"
    METHOD = "Method"
    IMPORT = "Import"
    VARIABLE = "Variable"


class RelationshipType(Enum):
    """Types of relationships in the graph database."""

    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS_FROM = "INHERITS_FROM"
    DEFINES = "DEFINES"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    LOCATED_IN = "LOCATED_IN"


@dataclass
class GraphNode:
    """Represents a node in the graph database."""

    node_type: NodeType
    properties: Dict[str, Any]
    labels: List[str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = [self.node_type.value]


@dataclass
class GraphRelationship:
    """Represents a relationship in the graph database."""

    relationship_type: RelationshipType
    from_node_id: str
    to_node_id: str
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class FileNode(GraphNode):
    """Specialized node for files."""

    def __init__(
        self,
        path: str,
        language: str,
        lines_of_code: int,
        docstring: Optional[str] = None,
        **kwargs
    ):
        properties = {
            "path": path,
            "language": language,
            "lines_of_code": lines_of_code,
            "docstring": docstring,
            "file_name": path.split("/")[-1],
            "file_extension": path.split(".")[-1] if "." in path else "",
            **kwargs,
        }
        super().__init__(NodeType.FILE, properties)


@dataclass
class DirectoryNode(GraphNode):
    """Specialized node for directories."""

    def __init__(self, path: str, name: str, **kwargs):
        properties = {
            "path": path,
            "name": name,
            "depth": len([p for p in path.split("/") if p]),
            **kwargs,
        }
        super().__init__(NodeType.DIRECTORY, properties)


@dataclass
class FunctionNode(GraphNode):
    """Specialized node for functions."""

    def __init__(
        self,
        name: str,
        file_path: str,
        line_number: int,
        parameters: List[str] = None,
        return_type: Optional[str] = None,
        docstring: Optional[str] = None,
        visibility: str = "public",
        is_async: bool = False,
        is_method: bool = False,
        **kwargs
    ):
        properties = {
            "name": name,
            "file_path": file_path,
            "line_number": line_number,
            "parameters": parameters or [],
            "return_type": return_type,
            "docstring": docstring,
            "visibility": visibility,
            "is_async": is_async,
            "is_method": is_method,
            "parameter_count": len(parameters) if parameters else 0,
            **kwargs,
        }
        super().__init__(NodeType.FUNCTION, properties)


@dataclass
class ClassNode(GraphNode):
    """Specialized node for classes."""

    def __init__(
        self,
        name: str,
        file_path: str,
        line_number: int,
        bases: List[str] = None,
        docstring: Optional[str] = None,
        method_count: int = 0,
        attribute_count: int = 0,
        **kwargs
    ):
        properties = {
            "name": name,
            "file_path": file_path,
            "line_number": line_number,
            "bases": bases or [],
            "docstring": docstring,
            "method_count": method_count,
            "attribute_count": attribute_count,
            "has_inheritance": len(bases) > 0 if bases else False,
            **kwargs,
        }
        super().__init__(NodeType.CLASS, properties)


@dataclass
class ImportNode(GraphNode):
    """Specialized node for imports."""

    def __init__(
        self,
        module: str,
        names: List[str] = None,
        alias: Optional[str] = None,
        is_from_import: bool = False,
        file_path: str = "",
        **kwargs
    ):
        properties = {
            "module": module,
            "names": names or [],
            "alias": alias,
            "is_from_import": is_from_import,
            "file_path": file_path,
            "import_count": len(names) if names else 1,
            **kwargs,
        }
        super().__init__(NodeType.IMPORT, properties)


@dataclass
class GraphQuery:
    """Represents a query to be executed against the graph database."""

    cypher_query: str
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class GraphQueryResult:
    """Represents the result of a graph database query."""

    records: List[Dict[str, Any]]
    summary: Dict[str, Any] = None

    def __post_init__(self):
        if self.summary is None:
            self.summary = {}


@dataclass
class BatchOperation:
    """Represents a batch operation for graph database."""

    operation_type: str  # "CREATE", "UPDATE", "DELETE"
    nodes: List[GraphNode] = None
    relationships: List[GraphRelationship] = None

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.relationships is None:
            self.relationships = []


@dataclass
class GraphIndexRequest:
    """Request to create an index in the graph database."""

    node_type: NodeType
    property_name: str
    index_type: str = "BTREE"  # BTREE, FULLTEXT, etc.


@dataclass
class GraphConstraintRequest:
    """Request to create a constraint in the graph database."""

    node_type: NodeType
    property_names: List[str]
    constraint_type: str = "UNIQUE"  # UNIQUE, EXISTS, etc.
