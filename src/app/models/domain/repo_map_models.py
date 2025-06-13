from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class LanguageType(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


class FunctionVisibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    INTERNAL = "internal"


@dataclass
class FunctionInfo:
    """Information about a function or method."""

    name: str
    parameters: List[str]
    return_type: Optional[str]
    docstring: Optional[str]
    line_number: int
    is_async: bool = False
    is_method: bool = False
    visibility: FunctionVisibility = FunctionVisibility.PUBLIC
    decorators: List[str] = None

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "docstring": self.docstring,
            "line_number": self.line_number,
            "is_async": self.is_async,
            "is_method": self.is_method,
            "visibility": self.visibility.value,
            "decorators": self.decorators,
        }


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    bases: List[str]
    methods: List[FunctionInfo]
    attributes: List[str]
    docstring: Optional[str]
    line_number: int
    decorators: List[str] = None

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "bases": self.bases,
            "methods": [method.to_dict() for method in self.methods],
            "attributes": self.attributes,
            "docstring": self.docstring,
            "line_number": self.line_number,
            "decorators": self.decorators,
        }


@dataclass
class ImportInfo:
    """Information about imports."""

    module: str
    names: List[str]  # specific imports, empty for whole module
    alias: Optional[str]
    is_from_import: bool
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "names": self.names,
            "alias": self.alias,
            "is_from_import": self.is_from_import,
            "line_number": self.line_number,
        }


@dataclass
class FileInfo:
    """Information about a single file."""

    path: str
    language: LanguageType
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[ImportInfo]
    exports: List[str]  # For JS/TS files
    variables: List[str]
    docstring: Optional[str]
    lines_of_code: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language.value,
            "functions": [func.to_dict() for func in self.functions],
            "classes": [cls.to_dict() for cls in self.classes],
            "imports": [imp.to_dict() for imp in self.imports],
            "exports": self.exports,
            "variables": self.variables,
            "docstring": self.docstring,
            "lines_of_code": self.lines_of_code,
        }


@dataclass
class DirectoryNode:
    """Represents a directory in the structure."""

    name: str
    type: str = "directory"
    children: Dict[str, Any] = None

    def __post_init__(self):
        if self.children is None:
            self.children = {}

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "type": self.type, "children": self.children}


@dataclass
class FileNode:
    """Represents a file in the structure."""

    name: str
    type: str = "file"
    language: str = "unknown"
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "language": self.language,
            "path": self.path,
        }


@dataclass
class SummaryStats:
    """Summary statistics for the repository."""

    total_files: int
    total_functions: int
    total_classes: int
    total_lines_of_code: int
    languages: Dict[str, int]
    files_by_language: Dict[str, List[str]]
    largest_files: List[Dict[str, Any]]
    most_complex_files: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepositoryMap:
    """Complete repository map."""

    root_path: str
    files: List[FileInfo]
    directory_structure: Dict[str, Any]
    dependency_graph: Dict[str, List[str]]
    summary_stats: SummaryStats
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {
                "generated_at": "",
                "generator_version": "1.0.0",
                "total_processing_time": 0.0,
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": self.root_path,
            "files": [file.to_dict() for file in self.files],
            "directory_structure": self.directory_structure,
            "dependency_graph": self.dependency_graph,
            "summary_stats": self.summary_stats.to_dict(),
            "metadata": self.metadata,
        }
