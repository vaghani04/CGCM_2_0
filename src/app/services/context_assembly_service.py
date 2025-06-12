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
        # if not query_results.get("found", False):
        #     return f"No relevant code context found for query: '{user_query}'"
        
        context_parts = []
        
        # Add a header
        context_parts.append(f"## Code Context for: {user_query}")
        context_parts.append("")  # Empty line
            
        # Process the results
        results = query_results
        template_used = "llm_generated"
        
        # For LLM-generated queries, we use dynamic formatting based on result structure
        if template_used == "llm_generated":
            context_parts.extend(self._format_llm_generated_results(results))
        else:
            # Legacy format handling for backwards compatibility
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
        
        return "\n".join(context_parts)
    
    def _format_llm_generated_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format results from LLM-generated Cypher queries."""
        # Group results by query description
        results_by_description = {}
        for result in results:
            description = result.get("query_description", "Other Results")
            if description not in results_by_description:
                results_by_description[description] = []
            results_by_description[description].append(result)
        
        # Format each group
        all_context_parts = []
        for description, grouped_results in results_by_description.items():
            context_parts = [f"### {description}\n"]
            
            # Determine what type of nodes these results contain
            result_type = self._detect_result_type(grouped_results)
            
            # Apply appropriate formatting based on detected type
            if result_type == "function":
                context_parts.extend(self._format_dynamic_function_results(grouped_results))
            elif result_type == "class":
                context_parts.extend(self._format_dynamic_class_results(grouped_results))
            elif result_type == "file":
                context_parts.extend(self._format_dynamic_file_results(grouped_results))
            elif result_type == "directory":
                context_parts.extend(self._format_dynamic_directory_results(grouped_results))
            elif result_type == "import":
                context_parts.extend(self._format_dynamic_import_results(grouped_results))
            else:
                # Generic formatting as a fallback
                context_parts.extend(self._format_dynamic_generic_results(grouped_results))
            
            all_context_parts.extend(context_parts)
            all_context_parts.append("")  # Add spacing between different result groups
        
        return all_context_parts
    
    def _detect_result_type(self, results: List[Dict[str, Any]]) -> str:
        """Detect the type of nodes in the results based on properties."""
        if not results:
            return "unknown"
        
        # Check for properties that indicate specific node types
        first_result = results[0]
        
        if any(k in first_result for k in ["function_name", "parameters", "return_type"]):
            return "function"
        elif any(k in first_result for k in ["class_name", "methods"]):
            return "class"
        elif "file_path" in first_result and not any(k in first_result for k in ["function_name", "class_name"]):
            return "file"
        elif "directory_path" in first_result or "path" in first_result and first_result.get("type") == "Directory":
            return "directory"
        elif "module" in first_result or "import" in first_result:
            return "import"
        else:
            return "generic"
    
    def _format_dynamic_function_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format function results with dynamic property handling."""
        context_parts = []
        
        for i, func in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            # Get common function properties with fallbacks
            name = func.get("function_name", func.get("name", "Unknown Function"))
            file_path = func.get("file_path", "Unknown location")
            line_number = func.get("line_number", "")
            docstring = func.get("docstring", func.get("documentation", "No documentation available"))
            
            # Handle parameters field which might be in different formats
            parameters = func.get("parameters", [])
            if isinstance(parameters, str):
                try:
                    parameters = json.loads(parameters)
                except:
                    parameters = parameters.split(",") if parameters else []
            
            param_str = ", ".join(parameters) if isinstance(parameters, list) else str(parameters)
            return_type = func.get("return_type", "")
            
            # Format function signature
            signature = f"{name}({param_str})"
            if return_type:
                signature += f" -> {return_type}"
            
            context_parts.append(f"**Function:** `{signature}`")
            
            # Location information
            location = f"{file_path}"
            if line_number:
                location += f":{line_number}"
            context_parts.append(f"**Location:** {location}")
            
            # Documentation
            context_parts.append(f"**Documentation:** {docstring}")
            
            # Add any other properties that might be present
            for key, value in func.items():
                if key not in ["function_name", "name", "file_path", "line_number", "docstring", 
                               "documentation", "parameters", "return_type", "query_description"]:
                    context_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        
        return context_parts
    
    def _format_dynamic_class_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format class results with dynamic property handling."""
        context_parts = []
        
        for i, cls in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            name = cls.get("class_name", cls.get("name", "Unknown Class"))
            file_path = cls.get("file_path", "Unknown location")
            line_number = cls.get("line_number", "")
            docstring = cls.get("docstring", cls.get("documentation", "No documentation available"))
            
            context_parts.append(f"**Class:** `{name}`")
            
            location = f"{file_path}"
            if line_number:
                location += f":{line_number}"
            context_parts.append(f"**Location:** {location}")
            
            context_parts.append(f"**Documentation:** {docstring}")
            
            # Handle methods if present
            methods = cls.get("methods", [])
            if methods:
                method_list = ", ".join(f"`{m}`" for m in methods)
                context_parts.append(f"**Methods:** {method_list}")
            
            # Add any other properties
            for key, value in cls.items():
                if key not in ["class_name", "name", "file_path", "line_number", "docstring", 
                               "documentation", "methods", "query_description"]:
                    context_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        
        return context_parts
    
    def _format_dynamic_file_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format file results with dynamic property handling."""
        context_parts = []
        
        for i, file in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            file_path = file.get("file_path", file.get("path", "Unknown file"))
            language = file.get("language", "")
            lines_of_code = file.get("lines_of_code", "")
            
            context_parts.append(f"**File:** `{file_path}`")
            
            if language:
                context_parts.append(f"**Language:** {language}")
            
            if lines_of_code:
                context_parts.append(f"**Lines of Code:** {lines_of_code}")
            
            # Dependencies if present
            dependencies = file.get("dependencies", [])
            if dependencies:
                context_parts.append("**Dependencies:**")
                for dep in dependencies:
                    context_parts.append(f"- `{dep}`")
            
            # Imports if present
            imports = file.get("imports", [])
            if imports:
                context_parts.append("**Imports:**")
                for imp in imports:
                    context_parts.append(f"- `{imp}`")
            
            # Add any other properties
            for key, value in file.items():
                if key not in ["file_path", "path", "language", "lines_of_code", 
                               "dependencies", "imports", "query_description"]:
                    context_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        
        return context_parts
    
    def _format_dynamic_directory_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format directory results with dynamic property handling."""
        context_parts = []
        
        for i, directory in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            dir_path = directory.get("directory_path", directory.get("path", "Unknown directory"))
            name = directory.get("name", os.path.basename(dir_path) if dir_path != "Unknown directory" else "Unknown")
            
            context_parts.append(f"**Directory:** `{dir_path}`")
            context_parts.append(f"**Name:** {name}")
            
            # Files if present
            files = directory.get("files", [])
            if files:
                context_parts.append("**Contains Files:**")
                for file in files[:10]:  # Limit to 10 files to avoid clutter
                    context_parts.append(f"- `{file}`")
                if len(files) > 10:
                    context_parts.append(f"- *...and {len(files) - 10} more files*")
            
            # Add any other properties
            for key, value in directory.items():
                if key not in ["directory_path", "path", "name", "files", "query_description"]:
                    context_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        
        return context_parts
    
    def _format_dynamic_import_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format import results with dynamic property handling."""
        context_parts = []
        
        for i, imp in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            module = imp.get("module", "Unknown module")
            file_path = imp.get("file_path", "Unknown location")
            
            context_parts.append(f"**Import:** `{module}`")
            context_parts.append(f"**From File:** `{file_path}`")
            
            # Names if present
            names = imp.get("names", [])
            if names:
                if isinstance(names, str):
                    try:
                        names = json.loads(names)
                    except:
                        names = names.split(",") if names else []
                
                names_list = ", ".join(f"`{n}`" for n in names)
                context_parts.append(f"**Imported Names:** {names_list}")
            
            # Add any other properties
            for key, value in imp.items():
                if key not in ["module", "file_path", "names", "query_description"]:
                    context_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        
        return context_parts
    
    def _format_dynamic_generic_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Format generic results when specific type can't be determined."""
        context_parts = []
        
        for i, result in enumerate(results[:self.max_context_items]):
            if i > 0:
                context_parts.append("")  # Add separator between items
            
            # Try to identify a name field
            name = result.get("name", 
                   result.get("function_name", 
                   result.get("class_name", 
                   result.get("file_path", 
                   result.get("path", "Unknown")))))
            
            # Try to identify a location field
            location = result.get("file_path", result.get("path", "Unknown location"))
            line_number = result.get("line_number", "")
            if line_number:
                location += f":{line_number}"
            
            context_parts.append(f"**Item:** `{name}`")
            context_parts.append(f"**Location:** {location}")
            
            # Add all other properties
            for key, value in result.items():
                if key not in ["name", "function_name", "class_name", "file_path", "path", 
                               "line_number", "query_description"]:
                    # Format the key for better readability
                    formatted_key = key.replace("_", " ").title()
                    context_parts.append(f"**{formatted_key}:** {value}")
        
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
            file_path = result.get("file_path", result.get("path"))
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
                            entity_name = result.get("name", result.get("function_name", result.get("class_name", "")))
                            break
                    
                    header = f"File: {path}" + (f" - {entity_name}" if entity_name else "")
                    snippets.append(f"\n**{header}**\n")
                    
                    # Detect language for syntax highlighting
                    language = self._detect_file_language(path)
                    snippets.append(f"```{language}")
                    
                    for i in range(start_line, end_line):
                        prefix = "→ " if i + 1 == line else "  "
                        snippets.append(f"{prefix}{i+1}: {lines[i].rstrip()}")
                    snippets.append("```\n")
                else:
                    # If no specific line, just show the first few lines
                    snippets.append(f"\n**File: {path}**\n")
                    
                    # Detect language for syntax highlighting
                    language = self._detect_file_language(path)
                    snippets.append(f"```{language}")
                    
                    for i, line in enumerate(lines[:self.max_context_lines]):
                        snippets.append(f"  {i+1}: {line.rstrip()}")
                    snippets.append("```\n")
            except Exception as e:
                print(f"Error extracting code snippet from {path}: {e}")
        
        return snippets
    
    def _detect_file_language(self, file_path: str) -> str:
        """Detect programming language based on file extension for syntax highlighting."""
        ext = os.path.splitext(file_path)[1].lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.md': 'markdown',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.sh': 'bash',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.sql': 'sql'
        }
        
        return language_map.get(ext, 'text') 