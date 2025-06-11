import subprocess
import os
import json
from typing import Any, Dict, Union, List
from fastapi import Depends
from src.app.models.schemas.grep_search_query_schema import (
    GrepSearchQueryRequest,
)
from pathlib import Path
from src.app.config.settings import settings
from src.app.services.openai_service import OpenAIService
from src.app.prompts.grep_search_command_making_prompt import (
    GREP_SEARCH_COMMAND_MAKING_SYSTEM_PROMPT,
    GREP_SEARCH_COMMAND_MAKING_USER_PROMPT
)
from src.app.utils.response_parser import parse_response
import asyncio

class GrepSearchUsecase:
    def __init__(
        self,
        openai_service: OpenAIService = Depends(OpenAIService),
    ):
        self.openai_service = openai_service
        
        # Ensure the intermediate_outputs directory exists
        os.makedirs("intermediate_outputs", exist_ok=True)

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
            return file_path.suffix.lower() in settings.REPO_MAP_SUPPORTED_EXTENSIONS
        
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
    
        with open("intermediate_outputs/project_structure.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(structure_lines))
        
        return "\n".join(structure_lines)

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
            print(f"Getting directory structure for {codebase_path}")
            directory_structure = await self.get_directory_structure(codebase_path, depth=3)
            
            # Step 2: Generate grep commands using LLM
            print(f"Generating grep commands for: {query}")
            grep_commands = await self._generate_grep_commands(query, directory_structure)
            
            # Step 3: Execute the generated grep commands
            print(f"Executing {len(grep_commands)} grep commands")
            search_results = await self._execute_grep_commands(grep_commands, codebase_path)
            
            # Step 4: Format and return results
            formatted_results = await self._format_search_results(search_results, query)
            
            return formatted_results
            
        except Exception as e:
            error_message = f"Error executing grep search: {str(e)}"
            print(error_message)
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
        with open("intermediate_outputs/grep_commands.json", "w") as f:
            json.dump(parsed_response, f, indent=2)
        
        # Validate the parsed response
        if not isinstance(parsed_response, dict):
            print(f"Warning: Expected dict response, got {type(parsed_response)}")
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
            print(f"Executing command {i+1}/{len(commands)}: {command['description']}")
            
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
        with open("intermediate_outputs/grep_search_results.json", "w") as f:
            json.dump(all_results, f, indent=2)
        
        return all_results
    
    async def _format_search_results(self, search_results: List[Dict[str, Any]], original_query: str) -> str:
        """
        Format the search results into a readable string format.
        
        Args:
            search_results: List of search results from grep commands
            original_query: The original user query
            
        Returns:
            Formatted results as a string
        """
        if not search_results:
            return f"No results found for query: '{original_query}'"
        
        formatted_output = []
        formatted_output.append(f"=== Grep Search Results for: '{original_query}' ===\n")
        
        total_matches = 0
        successful_commands = 0
        
        for result in search_results:
            command_desc = result.get("command_description", "Unknown command")
            command_reasoning = result.get("command_reasoning", "")
            status = result.get("status", "unknown")
            count = result.get("count", 0)
            
            formatted_output.append(f"Command {result.get('command_index', '?')}: {command_desc}")
            formatted_output.append(f"Reasoning: {command_reasoning}")
            formatted_output.append(f"Status: {status}")
            formatted_output.append(f"Matches found: {count}")
            
            if status == "success" and count > 0:
                successful_commands += 1
                total_matches += count
                
                # Add the actual search results
                results_text = result.get("results", "")
                if results_text and results_text != "No matches found":
                    formatted_output.append("Results:")
                    formatted_output.append(results_text)
            elif status == "error":
                error_msg = result.get("results", "Unknown error")
                formatted_output.append(f"Error: {error_msg}")
            else:
                formatted_output.append("No matches found for this command")
            
            formatted_output.append("-" * 80)
        
        # Add summary
        formatted_output.append(f"\n=== Search Summary ===")
        formatted_output.append(f"Total commands executed: {len(search_results)}")
        formatted_output.append(f"Successful commands: {successful_commands}")
        formatted_output.append(f"Total matches found: {total_matches}")
        
        final_output = "\n".join(formatted_output)
        
        # Save formatted output for debugging
        with open("intermediate_outputs/grep_search_formatted_output.txt", "w") as f:
            f.write(final_output)
        
        return final_output
        

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
