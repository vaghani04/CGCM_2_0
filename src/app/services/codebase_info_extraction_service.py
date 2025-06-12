import asyncio
import os
import subprocess
from typing import Dict, List, Any
from pathlib import Path
from src.app.config.settings import settings


class CodebaseInfoExtractionService:
    """Service to extract targeted information from codebase using smart grep commands"""
    
    def __init__(self):
        self.supported_extensions = settings.NL_INSIGHTS_SUPPORTED_EXTENSIONS
        self.excluded_dirs = settings.REPO_MAP_EXCLUDED_DIRS
        
    async def extract_codebase_info(self, codebase_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive information from codebase using targeted approaches
        
        Args:
            codebase_path: Path to the codebase
            
        Returns:
            Dictionary containing extracted information
        """
        try:
            directory_structure = await self.get_directory_structure(codebase_path, depth=4)

            code_patterns = await self._extract_code_patterns(codebase_path)
            documentation_content = await self._extract_documentation(codebase_path)

            return {
                "directory_structure": directory_structure,
                "code_patterns": code_patterns,
                "documentation_content": documentation_content
            }
        except Exception as e:
            return {
                "directory_structure": f"Error extracting directory structure: {str(e)}",
                "code_patterns": f"Error extracting code patterns: {str(e)}",
                "documentation_content": f"Error extracting documentation: {str(e)}"
            }
    
    async def get_directory_structure(self, codebase_path: str, depth: int = 2) -> str:
        """
        Async version of directory structure scanner.
        Returns directory structure as a formatted string.
        Ignores directories from settings.REPO_MAP_EXCLUDED_DIRS
        Only includes .py, .js, .ts files and directories containing them.
        """
        base_path = Path(codebase_path).resolve()
        
        def is_supported_file(file_path: Path) -> bool:
            """Check if file has supported extension"""
            return file_path.suffix.lower() in settings.NL_INSIGHTS_SUPPORTED_EXTENSIONS
        
        async def traverse(path: Path, current_depth: int) -> list[str]:
            if current_depth > depth:
                return []
            
            lines = []
            prefix = '│   ' * (current_depth - 1) + ('├── ' if current_depth > 0 else '')
            
            try:
                items = await asyncio.to_thread(lambda: sorted(path.iterdir(), key=lambda x: x.name))
            except (PermissionError, OSError):
                return []
            
            for item in items:
                if item.is_dir():
                    if item.name in settings.REPO_MAP_EXCLUDED_DIRS:
                        continue

                    sub_lines = await traverse(item, current_depth + 1)
                    if sub_lines:
                        lines.append(f"{prefix}{item.name}/")
                        lines.extend(sub_lines)
                
                elif item.is_file() and is_supported_file(item):
                    lines.append(f"{prefix}{item.name}")
            
            return lines
        
        structure_lines = [base_path.name] + await traverse(base_path, 1)
    
        with open("intermediate_outputs/nl_extraction_outputs/directory_structure.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(structure_lines))
        
        return "\n".join(structure_lines)
    
    def _format_structure(self, structure: Dict, indent: str = "") -> str:
        """Format directory structure as readable text"""
        result = []
        for key, value in structure.items():
            if isinstance(value, dict):
                result.append(f"{indent}{key}/")
                result.append(self._format_structure(value, indent + "  "))
            else:
                result.append(f"{indent}{key}")
        return "\n".join(filter(None, result))
    
    async def _extract_code_patterns(self, codebase_path: str) -> str:
        """Extract key code patterns using targeted grep commands"""
        patterns = []
        
        try:
            # FastAPI/Python patterns
            patterns.extend(self._grep_patterns(codebase_path, [
                # API Routes
                (r"@app\.(get|post|put|delete|patch)", "FastAPI Routes"),
                (r"@router\.(get|post|put|delete|patch)", "FastAPI Router Endpoints"),
                (r"app\.route\(", "Flask Routes"),
                
                # Models and Schemas
                (r"class.*\(BaseModel\)", "Pydantic Models"),
                (r"class.*\(.*Model\)", "Database Models"),
                (r"@dataclass", "Python Dataclasses"),
                
                # Middleware and Auth
                (r"@app\.middleware", "FastAPI Middleware"),
                (r"Depends\(", "FastAPI Dependencies"),
                (r"HTTPBearer|OAuth2", "Authentication Patterns"),
                
                # Database
                (r"SQLAlchemy|sessionmaker|Session", "SQLAlchemy Usage"),
                (r"MongoDB|pymongo|motor", "MongoDB Usage"),
                (r"redis|Redis", "Redis Usage"),
            ]))
            
            # Node.js/JavaScript patterns
            patterns.extend(self._grep_patterns(codebase_path, [
                # Express Routes
                (r"app\.(get|post|put|delete|patch)", "Express Routes"),
                (r"router\.(get|post|put|delete|patch)", "Express Router"),
                (r"export.*router", "Router Exports"),
                
                # Models and Schemas
                (r"new Schema\(", "Mongoose Schemas"),
                (r"interface.*\{", "TypeScript Interfaces"),
                (r"type.*=", "TypeScript Types"),
                
                # Middleware
                (r"app\.use\(", "Express Middleware"),
                (r"cors\(|helmet\(|morgan\(", "Common Middleware"),
                
                # Database
                (r"mongoose\.|connect\(", "Mongoose Usage"),
                (r"Pool\(|createConnection", "Database Connections"),
            ]))
            
            # Error handling and validation
            patterns.extend(self._grep_patterns(codebase_path, [
                (r"try:|except:|catch\(|throw", "Error Handling"),
                (r"validate|validator|ValidationError", "Validation Logic"),
                (r"logging\.|console\.(log|error|warn)", "Logging"),
            ]))
            
            # Extract key functions and classes with docstrings
            patterns.extend(self._extract_documented_code(codebase_path))
            
        except Exception as e:
            patterns.append(f"Error extracting patterns: {str(e)}")

        with open("intermediate_outputs/nl_extraction_outputs/code_patterns.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(patterns))
        
        return "\n".join(patterns) if patterns else "No code patterns found"
    
    def _grep_patterns(self, codebase_path: str, pattern_list: List[tuple]) -> List[str]:
        """Run ripgrep commands for given patterns and return results"""
        results = []
        
        for pattern, description in pattern_list:
            try:
                # Build the ripgrep command
                cmd_parts = ["rg", "--no-heading", "--line-number", "--color=never", "--max-count=10", "-i"]
                
                # Add include patterns for supported file extensions
                for ext in ['py', 'js', 'ts', 'jsx', 'tsx']:
                    cmd_parts.extend(["-g", f"*.{ext}"])
                
                # Add exclude patterns for excluded directories
                for exclude_dir in self.excluded_dirs:
                    cmd_parts.extend(["-g", f"!{exclude_dir}/*"])
                
                # Add the search pattern
                cmd_parts.append(pattern)
                
                # Execute the command using subprocess
                result = subprocess.run(
                    cmd_parts,
                    cwd=codebase_path,
                    capture_output=True,
                    text=True,
                    timeout=10,  # 10 second timeout
                )
                
                # Check if command executed successfully
                # ripgrep exit codes: 0 = found, 1 = not found, 2 = error
                if result.returncode == 0 and result.stdout.strip():
                    output_lines = result.stdout.strip().split('\n')
                    match_count = len(output_lines)
                    
                    if match_count > 0:
                        results.append(f"{description}: Found {match_count} matches")
                        
                        # Get a few sample matches (limit to 2 lines)
                        sample_lines = output_lines[:2]
                        for line in sample_lines:
                            if line.strip():
                                results.append(f"  Example: {line.strip()}")
                        
            except FileNotFoundError:
                # ripgrep not found, skip this pattern
                results.append(f"{description}: Error - ripgrep (rg) not found")
                continue
            except Exception:
                continue  # Skip patterns that fail
        
        return results
    
    def _extract_documented_code(self, codebase_path: str) -> List[str]:
        """Extract key functions/classes with their docstrings using ripgrep"""
        results = []
        
        try:
            # Search for function and class definitions using ripgrep
            patterns = [
                (r"^def\s+\w+", "Python Functions"),
                (r"^async\s+def\s+\w+", "Async Python Functions"),
                (r"^class\s+\w+", "Python Classes"),
                (r"function\s+\w+", "JavaScript Functions"),
                (r"class\s+\w+", "JavaScript/TypeScript Classes")
            ]
            
            for pattern, description in patterns:
                cmd_parts = ["rg", "--no-heading", "--line-number", "--color=never", "--max-count=5", "-i"]
                
                # Add include patterns for supported file extensions
                for ext in ['py', 'js', 'ts', 'jsx', 'tsx']:
                    cmd_parts.extend(["-g", f"*.{ext}"])
                
                # Add exclude patterns for excluded directories
                for exclude_dir in self.excluded_dirs:
                    cmd_parts.extend(["-g", f"!{exclude_dir}/*"])
                
                # Add the search pattern
                cmd_parts.append(pattern)
                
                # Execute the command using subprocess
                result = subprocess.run(
                    cmd_parts,
                    cwd=codebase_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    output_lines = result.stdout.strip().split('\n')
                    
                    if output_lines:
                        results.append(f"{description}:")
                        # Process each match
                        for line in output_lines[:3]:  # Limit to 3 examples
                            if ':' in line:
                                try:
                                    file_path, line_num, content = line.split(':', 2)
                                    rel_path = os.path.relpath(file_path, codebase_path)
                                    results.append(f"  {rel_path}:{line_num} - {content.strip()}")
                                except ValueError:
                                    continue
            
            # Also search for docstrings
            docstring_cmd_parts = ["rg", "--no-heading", "--line-number", "--color=never", "--max-count=3", "-i"]
            
            # Add include patterns for Python files only
            docstring_cmd_parts.extend(["-g", "*.py"])
            
            # Add exclude patterns for excluded directories
            for exclude_dir in self.excluded_dirs:
                docstring_cmd_parts.extend(["-g", f"!{exclude_dir}/*"])
            
            # Search for docstrings
            docstring_cmd_parts.append(r'""".*"""')
            
            docstring_result = subprocess.run(
                docstring_cmd_parts,
                cwd=codebase_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if docstring_result.returncode == 0 and docstring_result.stdout.strip():
                docstring_lines = docstring_result.stdout.strip().split('\n')
                if docstring_lines:
                    results.append("Documentation Strings:")
                    for line in docstring_lines[:2]:  # Limit to 2 examples
                        if ':' in line:
                            try:
                                file_path, line_num, content = line.split(':', 2)
                                rel_path = os.path.relpath(file_path, codebase_path)
                                # Truncate long docstrings
                                content_clean = content.strip()[:100]
                                if len(content.strip()) > 100:
                                    content_clean += "..."
                                results.append(f"  {rel_path}:{line_num} - {content_clean}")
                            except ValueError:
                                continue
                            
        except FileNotFoundError:
            results.append("Error: ripgrep (rg) not found")
        except Exception as e:
            results.append(f"Error extracting documented code: {str(e)}")
        
        return results
    
    async def _extract_documentation(self, codebase_path: str) -> str:
        """Extract content from documentation files using ripgrep"""
        doc_content = []
        
        try:
            # Find documentation files using ripgrep
            doc_extensions = ['md', 'txt', 'rst']
            
            cmd_parts = ["rg", "--files", "--color=never"]
            
            # Add include patterns for documentation file extensions
            for ext in doc_extensions:
                cmd_parts.extend(["-g", f"*.{ext}"])
            
            # Add exclude patterns for excluded directories
            for exclude_dir in self.excluded_dirs:
                cmd_parts.extend(["-g", f"!{exclude_dir}/*"])
            
            # Execute the command using subprocess
            result = subprocess.run(
                cmd_parts,
                cwd=codebase_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0 and result.stdout.strip():
                doc_files = result.stdout.strip().split('\n')
                
                for doc_file in doc_files[:5]:  # Limit to 5 files
                    if doc_file and doc_file.strip():
                        try:
                            full_path = os.path.join(codebase_path, doc_file)
                            if os.path.exists(full_path):
                                rel_path = os.path.relpath(full_path, codebase_path)
                                doc_content.append(f"\n--- {rel_path} ---")
                                
                                with open(full_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Get first 500 characters to avoid overwhelming context
                                    if len(content) > 1000:
                                        content = content[:1000] + "..."
                                    doc_content.append(content)
                                    
                        except Exception:
                            continue
                            
        except FileNotFoundError:
            doc_content.append("Error: ripgrep (rg) not found")
        except Exception as e:
            doc_content.append(f"Error extracting documentation: {str(e)}")
        
        with open("intermediate_outputs/nl_extraction_outputs/documentation_content.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(doc_content))
        
        return "\n".join(doc_content) if doc_content else "No documentation files found" 