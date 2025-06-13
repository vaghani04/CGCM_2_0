import os
import ast
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime

from src.app.config.settings import settings
from src.app.models.domain.repo_map_models import (
    RepositoryMap, FileInfo, FunctionInfo, ClassInfo, ImportInfo, SummaryStats,
    LanguageType, FunctionVisibility
)
from src.app.utils.logging_util import loggers

class RepositoryMapService:
    """Service for generating comprehensive repository maps."""
    
    def __init__(self):
        self.supported_extensions = {
            '.py': LanguageType.PYTHON,
            '.js': LanguageType.JAVASCRIPT,
            '.jsx': LanguageType.JAVASCRIPT,
            '.ts': LanguageType.TYPESCRIPT,
            '.tsx': LanguageType.TYPESCRIPT
        }
        
    async def generate_repository_map(self, codebase_path: str, output_file: Optional[str] = None) -> Dict:
        """Generate a complete repository map for the given codebase."""
        start_time = time.time()
        
        # Validate codebase path
        codebase_path = Path(codebase_path).resolve()
        if not codebase_path.exists():
            raise ValueError(f"Codebase path does not exist: {codebase_path}")
        
        # Find all supported files
        files_to_analyze = self._find_supported_files(codebase_path)
        
        if not files_to_analyze:
            raise ValueError(f"No supported files found in: {codebase_path}")
        
        # Analyze each file
        analyzed_files = []
        for file_path in files_to_analyze:
            try:
                file_info = await self._analyze_file(file_path)
                if file_info:
                    analyzed_files.append(file_info)
            except Exception as e:
                loggers["main"].error(f"Warning: Failed to analyze {file_path}: {e}")
                continue
        
        # Generate directory structure
        directory_structure = self._generate_directory_structure(codebase_path, files_to_analyze)
        
        # Generate dependency graph
        dependency_graph = self._generate_dependency_graph(analyzed_files)
        
        # Generate summary statistics
        summary_stats = self._generate_summary_stats(analyzed_files)
        
        # Create repository map
        end_time = time.time()
        processing_time = end_time - start_time
        
        repo_map = RepositoryMap(
            root_path=str(codebase_path),
            files=analyzed_files,
            directory_structure=directory_structure,
            dependency_graph=dependency_graph,
            summary_stats=summary_stats,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "generator_version": "1.0.0",
                "total_processing_time": processing_time,
                "total_files_processed": len(analyzed_files),
                "supported_languages": list(set(f.language.value for f in analyzed_files))
            }
        )
        
        # Save to file
        output_file = output_file or settings.REPO_MAP_OUTPUT_FILE
        await self._save_repository_map(repo_map, output_file)
        
        return {
            "repository_map_file": output_file,
            "total_files_analyzed": len(analyzed_files),
            "processing_time_seconds": round(processing_time, 2),
            "summary": summary_stats.to_dict(),
            "repo_map_data": repo_map.to_dict()
        }
    
    def _find_supported_files(self, root_path: Path) -> List[str]:
        """Find all supported files in the codebase."""
        supported_files = []
        
        for root, dirs, files in os.walk(root_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in settings.REPO_MAP_EXCLUDED_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                
                # Check file size
                try:
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    if file_size_mb > settings.REPO_MAP_MAX_FILE_SIZE_MB:
                        continue
                except OSError:
                    continue
                
                # Check file extension
                if file_path.suffix.lower() in self.supported_extensions:
                    supported_files.append(str(file_path))
        
        return supported_files
    
    async def _analyze_file(self, file_path: str) -> Optional[FileInfo]:
        """Analyze a single file based on its extension."""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        language = self.supported_extensions.get(extension, LanguageType.UNKNOWN)
        
        try:
            # Check if file exists first
            if not file_path.exists():
                loggers["main"].error(f"Warning: File does not exist: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if language == LanguageType.PYTHON:
                return await self._analyze_python_file(str(file_path), content)
            elif language in [LanguageType.JAVASCRIPT, LanguageType.TYPESCRIPT]:
                return await self._analyze_js_ts_file(str(file_path), content, language)
            else:
                # For other languages, return basic file info
                return FileInfo(
                    path=str(file_path),
                    language=language,
                    functions=[],
                    classes=[],
                    imports=[],
                    exports=[],
                    variables=[],
                    docstring=None,
                    lines_of_code=len(content.splitlines())
                )
        
        except FileNotFoundError as e:
            loggers["main"].error(f"Warning: File not found: {file_path} - {e}")
            return None
        except PermissionError as e:
            loggers["main"].error(f"Warning: Permission denied: {file_path} - {e}")
            return None
        except UnicodeDecodeError as e:
            loggers["main"].error(f"Warning: Unicode decode error in file {file_path}: {e}")
            return None
        except Exception as e:
            loggers["main"].error(f"Warning: Error analyzing file {file_path}: {type(e).__name__}: {e}")
            return None
    
    async def _analyze_python_file(self, file_path: str, content: str) -> FileInfo:
        """Analyze a Python file using AST parsing."""
        try:
            tree = ast.parse(content)
            
            functions = self._extract_python_functions(tree)
            classes = self._extract_python_classes(tree, content)
            imports = self._extract_python_imports(tree)
            variables = self._extract_python_variables(tree)
            docstring = ast.get_docstring(tree)
            
            return FileInfo(
                path=file_path,
                language=LanguageType.PYTHON,
                functions=functions,
                classes=classes,
                imports=imports,
                exports=[],  # Python doesn't have explicit exports
                variables=variables,
                docstring=docstring,
                lines_of_code=len(content.splitlines())
            )
        
        except SyntaxError as e:
            loggers["main"].error(f"Syntax error in Python file {file_path}: {e}")
            return FileInfo(
                path=file_path,
                language=LanguageType.PYTHON,
                functions=[],
                classes=[],
                imports=[],
                exports=[],
                variables=[],
                docstring=None,
                lines_of_code=len(content.splitlines())
            )
    
    def _extract_python_functions(self, tree: ast.AST) -> List[FunctionInfo]:
        """Extract function definitions from Python AST."""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip methods (they'll be handled in class analysis)
                if self._is_method(node, tree):
                    continue
                
                visibility = self._get_python_visibility(node.name)
                
                func_info = FunctionInfo(
                    name=node.name,
                    parameters=self._extract_python_parameters(node),
                    return_type=self._extract_python_return_type(node),
                    docstring=ast.get_docstring(node),
                    line_number=node.lineno,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    is_method=False,
                    visibility=visibility,
                    decorators=[self._decorator_to_string(d) for d in node.decorator_list]
                )
                functions.append(func_info)
        
        return functions
    
    def _extract_python_classes(self, tree: ast.AST, content: str) -> List[ClassInfo]:
        """Extract class definitions from Python AST."""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                attributes = []
                
                # Extract methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        visibility = self._get_python_visibility(item.name)
                        
                        method_info = FunctionInfo(
                            name=item.name,
                            parameters=self._extract_python_parameters(item),
                            return_type=self._extract_python_return_type(item),
                            docstring=ast.get_docstring(item),
                            line_number=item.lineno,
                            is_async=isinstance(item, ast.AsyncFunctionDef),
                            is_method=True,
                            visibility=visibility,
                            decorators=[self._decorator_to_string(d) for d in item.decorator_list]
                        )
                        methods.append(method_info)
                    
                    elif isinstance(item, ast.Assign):
                        # Extract class attributes
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                attributes.append(target.id)
                
                class_info = ClassInfo(
                    name=node.name,
                    bases=[self._extract_base_name(base) for base in node.bases],
                    methods=methods,
                    attributes=attributes,
                    docstring=ast.get_docstring(node),
                    line_number=node.lineno,
                    decorators=[self._decorator_to_string(d) for d in node.decorator_list]
                )
                classes.append(class_info)
        
        return classes
    
    def _extract_python_imports(self, tree: ast.AST) -> List[ImportInfo]:
        """Extract import statements from Python AST."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_info = ImportInfo(
                        module=alias.name,
                        names=[],
                        alias=alias.asname,
                        is_from_import=False,
                        line_number=node.lineno
                    )
                    imports.append(import_info)
            
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names] if node.names else []
                import_info = ImportInfo(
                    module=node.module or "",
                    names=names,
                    alias=None,
                    is_from_import=True,
                    line_number=node.lineno
                )
                imports.append(import_info)
        
        return imports
    
    def _extract_python_variables(self, tree: ast.AST) -> List[str]:
        """Extract module-level variable assignments."""
        variables = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append(target.id)
        
        return variables
    
    async def _analyze_js_ts_file(self, file_path: str, content: str, language: LanguageType) -> FileInfo:
        """Analyze JavaScript/TypeScript files using regex patterns."""
        functions = self._extract_js_functions(content)
        classes = self._extract_js_classes(content)
        imports = self._extract_js_imports(content)
        exports = self._extract_js_exports(content)
        variables = self._extract_js_variables(content)
        
        return FileInfo(
            path=file_path,
            language=language,
            functions=functions,
            classes=classes,
            imports=imports,
            exports=exports,
            variables=variables,
            docstring=self._extract_js_file_header_comment(content),
            lines_of_code=len(content.splitlines())
        )
    
    def _extract_js_functions(self, content: str) -> List[FunctionInfo]:
        """Extract function definitions using regex patterns."""
        functions = []
        
        # Function declaration patterns
        patterns = [
            # function name() {} or async function name() {}
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*{',
            # const/let/var name = function() {} or const name = async function() {}
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*{',
            # const name = () => {} or const name = async () => {}
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)(?:\s*:\s*([^=]+))?\s*=>\s*{',
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    name = match.group(1)
                    params_str = match.group(2) if len(match.groups()) > 1 else ""
                    return_type = match.group(3) if len(match.groups()) > 2 and match.group(3) else None
                    
                    # Parse parameters
                    params = self._parse_js_parameters(params_str)
                    
                    # Check if async
                    is_async = 'async' in line
                    
                    visibility = self._get_js_visibility(name)
                    
                    func_info = FunctionInfo(
                        name=name,
                        parameters=params,
                        return_type=return_type.strip() if return_type else None,
                        docstring=self._extract_js_function_comment(lines, i-1),
                        line_number=i,
                        is_async=is_async,
                        is_method=False,
                        visibility=visibility
                    )
                    functions.append(func_info)
        
        return functions
    
    def _extract_js_classes(self, content: str) -> List[ClassInfo]:
        """Extract class definitions using regex patterns."""
        classes = []
        
        # Class pattern
        class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
        method_pattern = r'(?:async\s+)?(?:static\s+)?(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*{'
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            class_match = re.search(class_pattern, line)
            
            if class_match:
                class_name = class_match.group(1)
                base_class = class_match.group(2) if class_match.group(2) else None
                
                # Extract methods from class body
                methods = []
                j = i + 1
                brace_count = 1
                
                while j < len(lines) and brace_count > 0:
                    current_line = lines[j]
                    brace_count += current_line.count('{') - current_line.count('}')
                    
                    method_match = re.search(method_pattern, current_line)
                    if method_match:
                        method_name = method_match.group(1)
                        params_str = method_match.group(2)
                        return_type = method_match.group(3) if method_match.group(3) else None
                        
                        params = self._parse_js_parameters(params_str)
                        is_async = 'async' in current_line
                        visibility = self._get_js_visibility(method_name)
                        
                        method_info = FunctionInfo(
                            name=method_name,
                            parameters=params,
                            return_type=return_type.strip() if return_type else None,
                            docstring=self._extract_js_function_comment(lines, j),
                            line_number=j + 1,
                            is_async=is_async,
                            is_method=True,
                            visibility=visibility
                        )
                        methods.append(method_info)
                    
                    j += 1
                
                class_info = ClassInfo(
                    name=class_name,
                    bases=[base_class] if base_class else [],
                    methods=methods,
                    attributes=[],  # Harder to extract statically in JS
                    docstring=self._extract_js_function_comment(lines, i),
                    line_number=i + 1
                )
                classes.append(class_info)
                i = j
            else:
                i += 1
        
        return classes
    
    def _extract_js_imports(self, content: str) -> List[ImportInfo]:
        """Extract import statements using regex patterns."""
        imports = []
        
        # Import patterns
        patterns = [
            # import { name1, name2 } from 'module'
            (r'import\s*{\s*([^}]+)\s*}\s*from\s*[\'"]([^\'"]+)[\'"]', True),
            # import * as name from 'module'
            (r'import\s*\*\s*as\s+(\w+)\s*from\s*[\'"]([^\'"]+)[\'"]', False),
            # import name from 'module'
            (r'import\s+(\w+)\s*from\s*[\'"]([^\'"]+)[\'"]', False),
            # import 'module'
            (r'import\s*[\'"]([^\'"]+)[\'"]', False),
        ]
        
        for pattern, is_named in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                if len(match.groups()) == 1:
                    # Simple import 'module'
                    import_info = ImportInfo(
                        module=match.group(1),
                        names=[],
                        alias=None,
                        is_from_import=False
                    )
                elif len(match.groups()) == 2:
                    if is_named:
                        # Named imports
                        names_str = match.group(1)
                        module = match.group(2)
                        names = [name.strip() for name in names_str.split(',')]
                        import_info = ImportInfo(
                            module=module,
                            names=names,
                            alias=None,
                            is_from_import=True
                        )
                    else:
                        # Default import or alias
                        name_or_alias = match.group(1)
                        module = match.group(2)
                        import_info = ImportInfo(
                            module=module,
                            names=[],
                            alias=name_or_alias,
                            is_from_import=False
                        )
                    
                imports.append(import_info)
        
        return imports
    
    def _extract_js_exports(self, content: str) -> List[str]:
        """Extract export statements."""
        exports = []
        
        # Export patterns
        patterns = [
            r'export\s+(?:const|let|var|function|class)\s+(\w+)',
            r'export\s+{\s*([^}]+)\s*}',
            r'export\s+default\s+(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if '{' in match.group(0):
                    # Named exports
                    names = [name.strip() for name in match.group(1).split(',')]
                    exports.extend(names)
                else:
                    exports.append(match.group(1))
        
        return exports
    
    def _extract_js_variables(self, content: str) -> List[str]:
        """Extract top-level variable declarations."""
        variables = []
        
        # Variable patterns (top-level)
        pattern = r'^(?:const|let|var)\s+(\w+)'
        
        for line in content.split('\n'):
            match = re.search(pattern, line.strip())
            if match:
                variables.append(match.group(1))
        
        return variables
    
    def _generate_directory_structure(self, root_path: Path, files: List[str]) -> Dict[str, any]:
        """Generate a hierarchical directory structure."""
        structure = {}
        
        for file_path in files:
            rel_path = Path(file_path).relative_to(root_path)
            parts = rel_path.parts
            
            current_level = structure
            for part in parts[:-1]:  # All parts except filename
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
            
            # Add the file
            filename = parts[-1]
            extension = Path(filename).suffix.lower()
            language = self.supported_extensions.get(extension, LanguageType.UNKNOWN)
            
            current_level[filename] = {
                'type': 'file',
                'language': language.value,
                'path': str(rel_path)
            }
        
        return structure
    
    def _generate_dependency_graph(self, files: List[FileInfo]) -> Dict[str, List[str]]:
        """Generate a dependency graph based on imports."""
        graph = defaultdict(list)
        
        # Create a mapping of module names to file paths
        module_to_file = {}
        for file_info in files:
            # For Python files, use the module path
            if file_info.language == LanguageType.PYTHON:
                module_path = file_info.path.replace('/', '.').replace('\\', '.').replace('.py', '')
                module_to_file[module_path] = file_info.path
            
            # For JS/TS files, use relative paths
            elif file_info.language in [LanguageType.JAVASCRIPT, LanguageType.TYPESCRIPT]:
                module_to_file[file_info.path] = file_info.path
        
        # Build dependency relationships
        for file_info in files:
            dependencies = []
            
            for import_info in file_info.imports:
                # Try to resolve import to actual file
                module = import_info.module
                
                # Handle relative imports
                if module.startswith('.'):
                    # Resolve relative import
                    base_dir = os.path.dirname(file_info.path)
                    resolved_path = os.path.normpath(os.path.join(base_dir, module))
                    if resolved_path in module_to_file:
                        dependencies.append(module_to_file[resolved_path])
                else:
                    # Direct module reference
                    if module in module_to_file:
                        dependencies.append(module_to_file[module])
            
            if dependencies:
                graph[file_info.path] = dependencies
        
        return dict(graph)
    
    def _generate_summary_stats(self, files: List[FileInfo]) -> SummaryStats:
        """Generate summary statistics for the repository."""
        languages = defaultdict(int)
        files_by_language = defaultdict(list)
        total_functions = 0
        total_classes = 0
        total_lines_of_code = 0
        
        file_complexity = []
        
        for file_info in files:
            languages[file_info.language.value] += 1
            total_functions += len(file_info.functions)
            total_classes += len(file_info.classes)
            total_lines_of_code += file_info.lines_of_code
            files_by_language[file_info.language.value].append(file_info.path)
            
            # Calculate complexity (functions + classes + imports)
            complexity = len(file_info.functions) + len(file_info.classes) + len(file_info.imports)
            file_complexity.append((file_info.path, complexity, file_info.lines_of_code))
        
        # Sort files by complexity and size
        largest_files = []
        most_complex_files = []
        
        if file_complexity:
            file_complexity_by_comp = sorted(file_complexity, key=lambda x: x[1], reverse=True)
            most_complex_files = [{'path': path, 'complexity': comp} for path, comp, _ in file_complexity_by_comp[:10]]
            
            file_complexity_by_size = sorted(file_complexity, key=lambda x: x[2], reverse=True)
            largest_files = [{'path': path, 'lines': lines} for path, _, lines in file_complexity_by_size[:10]]
        
        return SummaryStats(
            total_files=len(files),
            total_functions=total_functions,
            total_classes=total_classes,
            total_lines_of_code=total_lines_of_code,
            languages=dict(languages),
            files_by_language=dict(files_by_language),
            largest_files=largest_files,
            most_complex_files=most_complex_files
        )
    
    async def _save_repository_map(self, repo_map: RepositoryMap, output_file: str):
        """Save the repository map to a JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(repo_map.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Failed to save repository map to {output_file}: {e}")
    
    # Helper methods
    def _extract_python_parameters(self, node: ast.FunctionDef) -> List[str]:
        """Extract function parameters with type hints."""
        params = []
        
        for arg in node.args.args:
            param_str = arg.arg
            if arg.annotation:
                param_str += f": {self._annotation_to_string(arg.annotation)}"
            params.append(param_str)
        
        # Handle *args and **kwargs
        if node.args.vararg:
            vararg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg_str += f": {self._annotation_to_string(node.args.vararg.annotation)}"
            params.append(vararg_str)
        
        if node.args.kwarg:
            kwarg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg_str += f": {self._annotation_to_string(node.args.kwarg.annotation)}"
            params.append(kwarg_str)
        
        return params
    
    def _extract_python_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation."""
        if node.returns:
            return self._annotation_to_string(node.returns)
        return None
    
    def _annotation_to_string(self, annotation: ast.AST) -> str:
        """Convert AST annotation to string."""
        try:
            return ast.unparse(annotation)
        except:
            return str(annotation)
    
    def _decorator_to_string(self, decorator: ast.AST) -> str:
        """Convert decorator AST to string."""
        try:
            return ast.unparse(decorator)
        except:
            return str(decorator)
    
    def _extract_base_name(self, base: ast.AST) -> str:
        """Extract base class name."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{self._extract_base_name(base.value)}.{base.attr}"
        else:
            try:
                return ast.unparse(base)
            except:
                return str(base)
    
    def _is_method(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if function is a method of a class."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False
    
    def _get_python_visibility(self, name: str) -> FunctionVisibility:
        """Determine visibility based on Python naming convention."""
        if name.startswith('__') and name.endswith('__'):
            return FunctionVisibility.PUBLIC  # Special methods are public
        elif name.startswith('__'):
            return FunctionVisibility.PRIVATE
        elif name.startswith('_'):
            return FunctionVisibility.PROTECTED
        else:
            return FunctionVisibility.PUBLIC
    
    def _get_js_visibility(self, name: str) -> FunctionVisibility:
        """Determine visibility for JavaScript/TypeScript."""
        if name.startswith('_'):
            return FunctionVisibility.PRIVATE
        else:
            return FunctionVisibility.PUBLIC
    
    def _parse_js_parameters(self, params_str: str) -> List[str]:
        """Parse JavaScript function parameters."""
        if not params_str.strip():
            return []
        
        params = []
        for param in params_str.split(','):
            param = param.strip()
            if param:
                params.append(param)
        
        return params
    
    def _extract_js_function_comment(self, lines: List[str], line_index: int) -> Optional[str]:
        """Extract JSDoc comment above function."""
        if line_index <= 0:
            return None
        
        # Look for JSDoc comment above the function
        comment_lines = []
        i = line_index - 1
        
        while i >= 0 and (lines[i].strip().startswith('*') or 
                          lines[i].strip().startswith('/**') or
                          lines[i].strip().startswith('//')):
            comment_lines.insert(0, lines[i].strip())
            i -= 1
            if lines[i + 1].strip().startswith('/**'):
                break
        
        if comment_lines:
            return '\n'.join(comment_lines)
        
        return None
    
    def _extract_js_file_header_comment(self, content: str) -> Optional[str]:
        """Extract file header comment."""
        lines = content.split('\n')
        comment_lines = []
        
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if line.startswith('/**') or line.startswith('*') or line.startswith('//'):
                comment_lines.append(line)
            elif line and not line.startswith('import') and not line.startswith('export'):
                break
        
        if comment_lines:
            return '\n'.join(comment_lines)
        
        return None 