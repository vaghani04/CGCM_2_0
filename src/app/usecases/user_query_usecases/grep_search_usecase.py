import subprocess
import os
import json
from typing import Any, Dict, Union, List
from fastapi import Depends
from src.app.models.schemas.grep_search_query_schema import (
    GrepSearchQueryRequest,
)
from src.app.services.openai_service import OpenAIService
from src.app.prompts.grep_search_command_making_prompt import (
    GREP_SEARCH_COMMAND_MAKING_SYSTEM_PROMPT,
    GREP_SEARCH_COMMAND_MAKING_USER_PROMPT
)
from src.app.utils.response_parser import parse_response
from src.app.utils.codebase_overview_utils import get_directory_structure
from src.app.utils.logging_util import loggers

class GrepSearchUsecase:
    def __init__(
        self,
        openai_service: OpenAIService = Depends(OpenAIService),
    ):
        self.openai_service = openai_service

    async def execute(self, user_query_data: Dict[str, Any]) -> str:
        """
        Execute grep search command generation and execution based on user query.
        
        Args:
            user_query_data: Dictionary containing 'query' and 'codebase_path' keys
            
        Returns:
            Formatted search results as a string
        """
        try:
            query = user_query_data["query"]
            codebase_path = user_query_data["codebase_path"]
            
            # Step 1: Get directory structure
            loggers["main"].info(f"Getting directory structure for {codebase_path}")
            directory_structure = await get_directory_structure(codebase_path, depth=5)
            with open("intermediate_outputs/grep_search_outputs/directory_structure.txt", "w") as f:
                f.write(directory_structure)
            
            # Step 2: Generate grep commands using LLM
            loggers["main"].info(f"Generating grep commands for: {query}")
            grep_commands = await self._generate_grep_commands(query, directory_structure)
            
            # Step 3: Execute the generated grep commands
            loggers["main"].info(f"Executing {len(grep_commands)} grep commands")
            search_results = await self._execute_grep_commands(grep_commands, codebase_path)
            
            # Step 4: Format and return results
            formatted_results = await self._format_search_results(search_results, query)
            
            return formatted_results
            
        except Exception as e:
            error_message = f"Error executing grep search: {str(e)}"
            loggers["main"].error(error_message)
            return f"Failed to execute grep search. Error: {str(e)}"
    
    async def _generate_grep_commands(self, query: str, directory_structure: str) -> List[Dict[str, Any]]:
        """
        Generate grep commands using LLM.
        
        Args:
            query: The user's natural language query
            directory_structure: String representation of the directory structure
            
        Returns:
            List of grep command objects with query parameters
        """
        # Format the user prompt with the query and directory structure
        user_prompt = GREP_SEARCH_COMMAND_MAKING_USER_PROMPT.format(
            query=query,
            directory_structure=directory_structure
        )
        
        # Call the OpenAI service
        response = await self.openai_service.completions(
            system_prompt=GREP_SEARCH_COMMAND_MAKING_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        # Parse the response to extract the commands
        parsed_response = parse_response(response)
        
        # Save the parsed response for debugging
        with open("intermediate_outputs/grep_search_outputs/grep_commands.json", "w") as f:
            json.dump(parsed_response, f, indent=2)
        
        # Validate the parsed response
        if not isinstance(parsed_response, dict):
            loggers["main"].warning(f"Warning: Expected dict response, got {type(parsed_response)}")
            return []
        
        # Extract commands from the response
        commands = parsed_response.get("commands", [])
        
        # Validate command structure
        validated_commands = []
        for i, command in enumerate(commands):
            if isinstance(command, dict) and command.get("query"):
                validated_commands.append({
                    "query": command.get("query", ""),
                    "include_pattern": command.get("include_pattern", "*.py,*.js,*.ts"),
                    "exclude_pattern": command.get("exclude_pattern", ""),
                    "case_sensitive": command.get("case_sensitive", False),
                    "description": command.get("description", f"Search command {i+1}"),
                    "reasoning": command.get("reasoning", f"Generated command {i+1}")
                })
        
        return validated_commands
    
    async def _execute_grep_commands(self, commands: List[Dict[str, Any]], codebase_path: str) -> List[Dict[str, Any]]:
        """
        Execute multiple grep commands and collect results.
        
        Args:
            commands: List of grep command objects
            codebase_path: Path to the codebase
            
        Returns:
            List of results from each command
        """
        all_results = []
        
        for i, command in enumerate(commands):
            loggers["main"].info(f"Executing command {i+1}/{len(commands)}: {command['description']}")
            
            # Create a request object for the existing execute_grep_search method
            grep_request = {
                "query": command["query"],
                "include_pattern": command["include_pattern"],
                "exclude_pattern": command["exclude_pattern"],
                "case_sensitive": command["case_sensitive"],
                "codebase_path": codebase_path
            }
            
            # Execute the grep search
            result = await self.execute_grep_search(grep_request, codebase_path)
            
            # Add metadata to the result
            result["command_description"] = command["description"]
            result["command_reasoning"] = command["reasoning"]
            result["command_index"] = i + 1
            
            all_results.append(result)
        
        # Save all results for debugging
        with open("intermediate_outputs/grep_search_outputs/grep_search_results.json", "w") as f:
            json.dump(all_results, f, indent=2)
        
        return all_results
    
    async def _format_search_results(self, search_results: List[Dict[str, Any]], original_query: str) -> str:
        """
        Format the search results into a structured, machine-readable JSON format 
        optimized for autonomous agent consumption.
        
        Args:
            search_results: List of search results from grep commands
            original_query: The original user query
            
        Returns:
            JSON-formatted results as a string for autonomous agent processing
        """
        if not search_results:
            return json.dumps({
                "search_context": {
                    "original_query": original_query,
                    "total_matches": 0,
                    "status": "no_results"
                },
                "findings": [],
                "summary": "No relevant code patterns found for the specified query."
            }, indent=2)
        
        # Process and categorize findings
        code_findings = []
        total_matches = 0
        successful_searches = 0
        
        for result in search_results:
            status = result.get("status", "unknown")
            count = result.get("count", 0)
            
            if status == "success" and count > 0:
                successful_searches += 1
                total_matches += count
                
                results_text = result.get("results", "")
                if results_text and results_text != "No matches found":
                    # Parse grep output into structured findings
                    findings = self._parse_grep_output(
                        results_text, 
                        result.get("command_description", ""),
                        result.get("command_reasoning", "")
                    )
                    code_findings.extend(findings)
        
        # Create structured output optimized for autonomous agents
        structured_output = {
            "search_context": {
                "original_query": original_query,
                "total_matches": total_matches,
                "successful_searches": successful_searches,
                "status": "success" if total_matches > 0 else "no_matches"
            },
            "findings": code_findings[:20],  # Limit to top 20 most relevant
            "summary": self._generate_concise_summary(code_findings, original_query)
        }
        
        # Save both structured and debug versions
        with open("intermediate_outputs/grep_search_outputs/grep_search_structured_output.json", "w") as f:
            json.dump(structured_output, f, indent=2)
        
        return json.dumps(structured_output, indent=2)
    
    def _parse_grep_output(self, grep_output: str, search_description: str, reasoning: str) -> List[Dict[str, Any]]:
        """
        Parse raw grep output into structured findings for autonomous agents.
        
        Args:
            grep_output: Raw output from ripgrep
            search_description: Description of what was searched
            reasoning: Why this search was performed
            
        Returns:
            List of structured findings
        """
        findings = []
        lines = grep_output.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                try:
                    # Parse grep output format: file_path:line_number:content
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        file_path = parts[0].strip()
                        line_number = parts[1].strip()
                        content = parts[2].strip()
                        
                        # Categorize the finding
                        finding_type = self._categorize_finding(content)
                        
                        finding = {
                            "file_path": file_path,
                            "line_number": int(line_number) if line_number.isdigit() else line_number,
                            "content": content,
                            "type": finding_type,
                            "search_context": {
                                "description": search_description,
                                "reasoning": reasoning
                            },
                            "relevance_score": self._calculate_relevance_score(content, finding_type)
                        }
                        findings.append(finding)
                except (ValueError, IndexError):
                    # Skip malformed lines
                    continue
        
        # Sort by relevance score
        findings.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return findings
    
    def _categorize_finding(self, content: str) -> str:
        """
        Categorize code findings for autonomous agent understanding.
        
        Args:
            content: Code content line
            
        Returns:
            Category type string
        """
        content_lower = content.lower().strip()
        
        # Function definitions
        if any(pattern in content_lower for pattern in ['def ', 'function ', 'const ', 'async def']):
            return "function_definition"
        
        # Class definitions
        if any(pattern in content_lower for pattern in ['class ', 'interface ', 'type ']):
            return "class_definition"
        
        # Import statements
        if any(pattern in content_lower for pattern in ['import ', 'from ', 'require(', '#include']):
            return "import_statement"
        
        # Error handling
        if any(pattern in content_lower for pattern in ['error', 'exception', 'throw', 'raise', 'catch', 'try']):
            return "error_handling"
        
        # Configuration
        if any(pattern in content_lower for pattern in ['config', 'settings', 'env', 'api_key']):
            return "configuration"
        
        # Comments and documentation
        if any(pattern in content_lower for pattern in ['todo', 'fixme', 'note', 'bug', 'hack', '//', '#', '"""']):
            return "documentation"
        
        # Variable declarations
        if any(pattern in content_lower for pattern in ['let ', 'var ', 'const ', '= ']):
            return "variable_declaration"
        
        return "code_reference"
    
    def _calculate_relevance_score(self, content: str, finding_type: str) -> float:
        """
        Calculate relevance score for prioritizing findings.
        
        Args:
            content: Code content
            finding_type: Type of finding
            
        Returns:
            Relevance score (0.0 - 1.0)
        """
        base_scores = {
            "function_definition": 0.9,
            "class_definition": 0.8,
            "error_handling": 0.7,
            "import_statement": 0.6,
            "configuration": 0.5,
            "variable_declaration": 0.4,
            "documentation": 0.3,
            "code_reference": 0.2
        }
        
        base_score = base_scores.get(finding_type, 0.1)
        
        # Boost score for common important patterns
        content_lower = content.lower()
        if any(pattern in content_lower for pattern in ['main', 'init', 'setup', 'config']):
            base_score += 0.1
        
        # Reduce score for test files
        if any(pattern in content_lower for pattern in ['test', 'spec', 'mock']):
            base_score -= 0.2
        
        return max(0.0, min(1.0, base_score))
    
    def _generate_concise_summary(self, findings: List[Dict[str, Any]], original_query: str) -> str:
        """
        Generate a concise summary for autonomous agents.
        
        Args:
            findings: List of code findings
            original_query: Original user query
            
        Returns:
            Concise summary string
        """
        if not findings:
            return f"No relevant code found for: {original_query}"
        
        # Count findings by type
        type_counts = {}
        file_counts = {}
        
        for finding in findings:
            finding_type = finding.get("type", "unknown")
            file_path = finding.get("file_path", "unknown")
            
            type_counts[finding_type] = type_counts.get(finding_type, 0) + 1
            file_counts[file_path] = file_counts.get(file_path, 0) + 1
        
        # Generate concise summary
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        summary_parts = [
            f"Found {len(findings)} relevant code references for '{original_query}'.",
            f"Primary patterns: {', '.join([f'{t[0]}({t[1]})' for t in top_types])}.",
            f"Key files: {', '.join([t[0] for t in top_files])}."
        ]
        
        return " ".join(summary_parts)
        

    async def execute_grep_search(
        self, request: Union[GrepSearchQueryRequest, Dict[str, Any]], codebase_path: str = None
    ) -> Dict[str, Any]:
        """
        Execute a grep search using ripgrep directly with subprocess.

        Args:
            request: The grep search request (can be GrepSearchQueryRequest object or dict)
            workspace_path: The workspace path (optional, will be extracted from request if not provided)

        Returns:
            A dictionary with the search results and metadata
        """
        # Handle both dict and GrepSearchQueryRequest inputs
        if isinstance(request, dict):
            query = request.get("query", "")
            case_sensitive = request.get("case_sensitive", False)
            include_pattern = request.get("include_pattern")
            exclude_pattern = request.get("exclude_pattern")
            codebase_path = codebase_path or request.get("codebase_path")
        else:
            query = request.query
            case_sensitive = request.case_sensitive
            include_pattern = request.include_pattern
            exclude_pattern = request.exclude_pattern
            codebase_path = codebase_path or request.codebase_path

        # Validate inputs
        if not query or not query.strip():
            return {
                "results": "Error: Query cannot be empty",
                "count": 0,
                "status": "error",
            }

        if not codebase_path or not os.path.exists(codebase_path):
            return {
                "results": f"Error: Invalid workspace path: {codebase_path}",
                "count": 0,
                "status": "error",
            }

        try:
            # Build the ripgrep command
            cmd_parts = ["rg", "--no-heading", "--line-number", "--color=never", "--max-count=50"]

            if not case_sensitive:
                cmd_parts.append("-i")

            # Only add include/exclude patterns if they are meaningful
            if include_pattern and include_pattern.strip():
                # Handle multiple patterns separated by commas
                patterns = [p.strip() for p in include_pattern.split(",") if p.strip()]
                for pattern in patterns:
                    cmd_parts.extend(["-g", pattern])

            if exclude_pattern and exclude_pattern.strip():
                # Handle multiple patterns separated by commas
                patterns = [p.strip() for p in exclude_pattern.split(",") if p.strip()]
                for pattern in patterns:
                    cmd_parts.extend(["-g", f"!{pattern}"])

            # Add the search query
            cmd_parts.append(query)

            # Execute the command using subprocess
            result = subprocess.run(
                cmd_parts,
                cwd=codebase_path,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )

            # Check if command executed successfully
            # ripgrep exit codes: 0 = found, 1 = not found, 2 = error
            if result.returncode == 2:
                error_msg = result.stderr.strip() if result.stderr else "Unknown ripgrep error"
                return {
                    "results": f"Error executing search: {error_msg}",
                    "count": 0,
                    "status": "error",
                }

            output = result.stdout.strip()
            output_lines = output.split("\n") if output else []

            # Process the output (limit to max 50 matches)
            matches = []
            match_count = 0

            for line in output_lines:
                if line.strip() and match_count < 50:
                    matches.append(line.strip())
                    match_count += 1

            return {
                "results": (
                    "\n".join(matches) if matches else "No matches found"
                ),
                "count": match_count,
                "status": "success",
            }

        except subprocess.TimeoutExpired:
            return {
                "results": "Error: Search operation timed out (30 seconds)",
                "count": 0,
                "status": "error",
            }
        except FileNotFoundError:
            return {
                "results": "Error: ripgrep (rg) command not found. Please install ripgrep.",
                "count": 0,
                "status": "error",
            }
        except Exception as e:
            return {
                "results": f"Error executing search: {str(e)}",
                "count": 0,
                "status": "error",
            }
