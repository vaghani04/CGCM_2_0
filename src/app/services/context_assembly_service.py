import json
import os
from typing import Dict, List, Any

class ContextAssemblyService:
    """Service to assemble the final context from GraphDB query results."""
    
    def __init__(self):
        # Maximum number of items to include in the context
        self.max_context_items = 5
        # Maximum number of lines to extract around a code entity
        self.max_context_lines = 20
    
    async def assemble_context(self, query_results: Dict[str, Any], user_query: str) -> str:
        """
        Assemble the final context from the GraphDB query results.
        
        Args:
            query_results: The results from the GraphDB query
            user_query: The original user query
            
        Returns:
            A formatted string with the assembled context
        """
        if not query_results.get("found", False):
            return f"No relevant code context found for query: '{user_query}'"
        
        context_parts = []
        
        # Add a header
        context_parts.append(f"## Code Context for: {user_query}")
        context_parts.append("")  # Empty line
        
        # Process the results
        results = query_results.get("results", [])
        template_used = query_results.get("template_used", "generic")
        
        # Format the context based on the template/result type
        if template_used == "function_info":
            context_parts.extend(self._format_function_info(results))
        elif template_used == "function_usage":
            context_parts.extend(self._format_function_usage(results))
        elif template_used == "class_info":
            context_parts.extend(self._format_class_info(results))
        elif template_used == "file_dependencies":
            context_parts.extend(self._format_file_dependencies(results))
        elif template_used == "file_imports":
            context_parts.extend(self._format_file_imports(results))
        elif template_used == "class_implementations":
            context_parts.extend(self._format_class_implementations(results))
        else:
            # Generic formatting for search results
            context_parts.extend(self._format_generic_results(results))
        
        # Add relevant code snippets if available
        file_paths = self._extract_file_paths(results)
        code_snippets = await self._extract_code_snippets(file_paths, results)
        if code_snippets:
            context_parts.append("\n### Relevant Code Snippets\n")
            context_parts.extend(code_snippets)
        
        return context_parts
    
    def _format_function_info(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format function information."""
        context_parts = ["### Function Information\n"]
        
        for i, func in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            name = func.get("function_name", "Unknown")
            file_path = func.get("file_path", "Unknown")
            line_number = func.get("line_number", "Unknown")
            docstring = func.get("docstring") or "No documentation available"
            parameters = func.get("parameters", [])
            return_type = func.get("return_type") or "Unknown"
            
            # Format parameters
            if isinstance(parameters, str):
                try:
                    parameters = json.loads(parameters)
                except:
                    parameters = parameters.split(",") if parameters else []
            
            param_str = ", ".join(parameters) if isinstance(parameters, list) else str(parameters)
            
            context_parts.append(f"**Function:** `{name}({param_str}) -> {return_type}`")
            context_parts.append(f"**Location:** {file_path}:{line_number}")
            context_parts.append(f"**Documentation:** {docstring}")
        
        return context_parts
    
    def _format_function_usage(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format function usage information."""
        context_parts = ["### Function Usage\n"]
        
        for i, usage in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            caller = usage.get("caller_function", "Unknown")
            caller_file = usage.get("caller_file_path", "Unknown")
            caller_line = usage.get("caller_line_number", "Unknown")
            called = usage.get("called_function", "Unknown")
            
            context_parts.append(f"**Caller:** `{caller}`")
            context_parts.append(f"**Calls:** `{called}`")
            context_parts.append(f"**Location:** {caller_file}:{caller_line}")
        
        return context_parts
    
    def _format_class_info(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format class information."""
        context_parts = ["### Class Information\n"]
        
        for i, cls in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            name = cls.get("class_name", "Unknown")
            file_path = cls.get("file_path", "Unknown")
            line_number = cls.get("line_number", "Unknown")
            docstring = cls.get("docstring") or "No documentation available"
            methods = cls.get("methods", [])
            
            context_parts.append(f"**Class:** `{name}`")
            context_parts.append(f"**Location:** {file_path}:{line_number}")
            context_parts.append(f"**Documentation:** {docstring}")
            
            if methods:
                method_list = ", ".join(f"`{m}`" for m in methods)
                context_parts.append(f"**Methods:** {method_list}")
        
        return context_parts
    
    def _format_file_dependencies(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format file dependency information."""
        context_parts = ["### File Dependencies\n"]
        
        for i, dep in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            file_path = dep.get("file_path", "Unknown")
            dependencies = dep.get("dependencies", [])
            
            context_parts.append(f"**File:** `{file_path}`")
            
            if dependencies:
                context_parts.append("**Dependencies:**")
                for d in dependencies:
                    context_parts.append(f"- `{d}`")
        
        return context_parts
    
    def _format_file_imports(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format file import information."""
        context_parts = ["### File Imports\n"]
        
        # Group by imported file
        imports_by_file = {}
        for imp in results:
            imported_file = imp.get("imported_file", "Unknown")
            file_path = imp.get("file_path", "Unknown")
            
            if imported_file not in imports_by_file:
                imports_by_file[imported_file] = []
            
            imports_by_file[imported_file].append(file_path)
        
        # Format the grouped imports
        for i, (imported_file, importers) in enumerate(list(imports_by_file.items())[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            context_parts.append(f"**Module:** `{imported_file}`")
            context_parts.append("**Imported by:**")
            for importer in importers:
                context_parts.append(f"- `{importer}`")
        
        return context_parts
    
    def _format_class_implementations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format class implementation information."""
        context_parts = ["### Class Implementations\n"]
        
        for i, impl in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            name = impl.get("class_name", "Unknown")
            file_path = impl.get("file_path", "Unknown")
            docstring = impl.get("docstring") or "No documentation available"
            
            context_parts.append(f"**Class:** `{name}`")
            context_parts.append(f"**Location:** {file_path}")
            context_parts.append(f"**Documentation:** {docstring}")
        
        return context_parts
    
    def _format_generic_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format generic search results."""
        context_parts = ["### Search Results\n"]
        
        for i, result in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            name = result.get("name", "Unknown")
            entity_type = result.get("entity_type", "Unknown")
            file_path = result.get("file_path", "Unknown")
            line_number = result.get("line_number", "Unknown")
            docstring = result.get("docstring") or "No documentation available"
            
            location = f"{file_path}:{line_number}" if line_number else file_path
            
            context_parts.append(f"**{entity_type}:** `{name}`")
            context_parts.append(f"**Location:** {location}")
            context_parts.append(f"**Documentation:** {docstring}")
        
        return context_parts
    
    def _extract_file_paths(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract file paths and line numbers from results."""
        file_paths = []
        
        for result in results[:self.max_context_items]:
            file_path = result.get("file_path")
            if not file_path:
                continue
                
            line_number = result.get("line_number")
            if line_number:
                file_paths.append({
                    "path": file_path,
                    "line": int(line_number) if isinstance(line_number, (int, str)) else None
                })
            else:
                file_paths.append({"path": file_path, "line": None})
        
        return file_paths
    
    async def _extract_code_snippets(self, file_paths: List[Dict[str, Any]], 
                                   results: List[Dict[str, Any]]) -> List[str]:
        """
        Extract code snippets from the files.
        
        Args:
            file_paths: List of dictionaries with file paths and line numbers
            results: The original query results
            
        Returns:
            List of formatted code snippets
        """
        snippets = []
        
        for file_info in file_paths:
            path = file_info.get("path")
            line = file_info.get("line")
            
            if not path or not os.path.exists(path):
                continue
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if line and 0 < line <= len(lines):
                    # Extract a context window around the line
                    start_line = max(0, line - self.max_context_lines // 2)
                    end_line = min(len(lines), line + self.max_context_lines // 2)
                    
                    # Find entity name if available
                    entity_name = ""
                    for result in results:
                        if result.get("file_path") == path and result.get("line_number") == line:
                            entity_name = result.get("name", "")
                            break
                    
                    header = f"File: {path}" + (f" - {entity_name}" if entity_name else "")
                    snippets.append(f"\n**{header}**\n")
                    snippets.append("```python")
                    for i in range(start_line, end_line):
                        prefix = "→ " if i + 1 == line else "  "
                        snippets.append(f"{prefix}{i+1}: {lines[i].rstrip()}")
                    snippets.append("```\n")
                else:
                    # If no specific line, just show the first few lines
                    snippets.append(f"\n**File: {path}**\n")
                    snippets.append("```python")
                    for i, line in enumerate(lines[:self.max_context_lines]):
                        snippets.append(f"  {i+1}: {line.rstrip()}")
                    snippets.append("```\n")
            except Exception as e:
                print(f"Error extracting code snippet from {path}: {e}")
        
        return snippets 