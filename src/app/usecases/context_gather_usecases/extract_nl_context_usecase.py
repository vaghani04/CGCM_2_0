import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import Depends

from src.app.config.test_queries import NL_CONTEXT_QUERIES
from src.app.prompts.nl_context_extraction_prompt import (
    GEN_NL_CONTEXT_SYSTEM_PROMPT,
    GEN_NL_CONTEXT_USER_PROMPT,
)
from src.app.services.codebase_info_extraction_service import (
    CodebaseInfoExtractionService,
)
from src.app.services.file_storage_service import FileStorageService
from src.app.services.graphdb_query_service import GraphDBQueryService
from src.app.services.openai_service import OpenAIService
from src.app.usecases.user_query_usecases.repo_map_usecase import RepoMapUsecase
from src.app.utils.logging_util import loggers
from src.app.utils.response_parser import parse_response


class ExtractNLContextUseCase:
    def __init__(
        self,
        codebase_info_extraction_service: CodebaseInfoExtractionService = Depends(
            CodebaseInfoExtractionService
        ),
        openai_service: OpenAIService = Depends(OpenAIService),
        file_storage_service: FileStorageService = Depends(FileStorageService),
        graphdb_query_service: GraphDBQueryService = Depends(
            GraphDBQueryService
        ),
        repo_map_usecase: RepoMapUsecase = Depends(RepoMapUsecase),
    ):
        self.codebase_info_extraction_service = codebase_info_extraction_service
        self.openai_service = openai_service
        self.file_storage_service = file_storage_service
        self.graphdb_query_service = graphdb_query_service
        self.repo_map_usecase = repo_map_usecase

    async def extract_nl_context_from_repo_map(self) -> Dict[str, Any]:
        """
        Extract natural language context from codebase using repomap's cypher queries executions
        """
        try:
            nl_context_queries = NL_CONTEXT_QUERIES
            # Execute all queries in parallel
            loggers["main"].info(
                f"Executing {len(nl_context_queries)} cypher queries in parallel..."
            )

            results = await self.repo_map_usecase._execute_queries_parallel(
                nl_context_queries
            )

            return results

        except Exception as e:
            loggers["main"].error(
                f"Error extracting NL context from repo map: {e}"
            )
            return {
                "success": False,
                "error": f"Error extracting NL context from repo map: {str(e)}",
                "nl_context": None,
            }

    async def extract_nl_context(
        self, codebase_path: str, git_branch_name: str
    ) -> Dict[str, Any]:
        """
        Extract natural language context from codebase using LLM analysis

        Args:
            codebase_path: Path to the codebase to analyze

        Returns:
            Dictionary containing operation result and insights file path
        """
        try:

            codebase_info_task = (
                self.codebase_info_extraction_service.extract_codebase_info(
                    codebase_path, git_branch_name
                )
            )
            codebase_info_from_repo_map_task = (
                self.extract_nl_context_from_repo_map()
            )

            # Create Tasks from the coroutines so we can check their status
            task1 = asyncio.create_task(codebase_info_task)
            task2 = asyncio.create_task(codebase_info_from_repo_map_task)

            # Wait for first task to complete
            codebase_info, is_previous_usable = await task1

            # If first task indicates we can use previous data, cancel second task and return
            if is_previous_usable:
                # Cancel the second task if it's not done
                if not task2.done():
                    task2.cancel()
                return {
                    "success": True,
                    "error": None,
                    "insights_file_path": None,
                    "codebase_info": codebase_info,
                }

            # If we need new data, wait for second task
            codebase_info_from_repo_map = await task2

            insights = await self._generate_insights_with_llm(
                codebase_path, codebase_info, codebase_info_from_repo_map
            )

            await self._store_insights(codebase_path, git_branch_name, insights)

            stats = self._generate_statistics(insights, codebase_info)

            return stats

        except Exception as e:
            return {
                "success": False,
                "error": f"Error extracting natural language context: {str(e)}",
                "insights_file_path": None,
            }

    async def _generate_insights_with_llm(
        self,
        codebase_path: str,
        codebase_info: Dict[str, Any],
        codebase_info_from_repo_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate insights using LLM analysis"""
        try:

            user_prompt = GEN_NL_CONTEXT_USER_PROMPT.format(
                directory_structure=codebase_info.get(
                    "directory_structure", "Not available"
                ),
                code_patterns=codebase_info.get(
                    "code_patterns", "Not available"
                ),
                documentation_content=codebase_info.get(
                    "documentation_content", "Not available"
                ),
                codebase_path=codebase_path,
                codebase_info_from_repo_map=codebase_info_from_repo_map,
            )

            response = await self.openai_service.completions(
                user_prompt=user_prompt,
                system_prompt=GEN_NL_CONTEXT_SYSTEM_PROMPT,
                temperature=0.1,
            )

            parsed_response = parse_response(response)

            with open(
                "intermediate_outputs/nl_context_gather_outputs/parsed_llm_response.json",
                "w",
            ) as f:
                json.dump(parsed_response, f, indent=2)

            return parsed_response

        except Exception as e:
            return {
                "features": [],
                "code_hierarchy": f"Error during LLM analysis: {str(e)}",
                "codebase_flow": f"Error during LLM analysis: {str(e)}",
                "intent_of_codebase": f"Error during LLM analysis: {str(e)}",
                "error": str(e),
            }

    async def _store_insights(
        self, codebase_path: str, git_branch_name: str, insights: Dict[str, Any]
    ) -> str:
        """Store insights using existing file storage service"""
        try:
            # Create storage key similar to merkle tree storage
            storage_key = f"{codebase_path}:{git_branch_name}"
            await self.file_storage_service.store_in_file_storage(
                storage_key, insights, file_name="nl_insights.json"
            )

        except Exception as e:
            raise Exception(f"Failed to store insights: {str(e)}")

    def _get_existing_insights(
        self, codebase_path: str
    ) -> Optional[Dict[str, Any]]:
        """Get existing insights if they exist"""
        try:
            workspace_dir = self.file_storage_service._get_workspace_dir(
                codebase_path
            )
            insights_file_path = workspace_dir / "nl_insights.json"

            if insights_file_path.exists():
                with open(insights_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "insights": data.get("insights", {}),
                    "file_path": str(insights_file_path),
                }
            return None
        except:
            return None

    def _generate_statistics(
        self, insights: Dict[str, Any], codebase_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate statistics about the extracted insights"""
        stats = {
            "used_from_stored_data": False,
            "total_features": len(insights.get("features", [])),
            "total_functional_requirements": 0,
            "total_non_functional_requirements": 0,
            "total_actionable_insights": 0,
            "has_code_hierarchy": bool(insights.get("code_hierarchy")),
            "has_codebase_flow": bool(insights.get("codebase_flow")),
            "has_intent_analysis": bool(insights.get("intent_of_codebase")),
        }

        # Count requirements and insights
        for feature in insights.get("features", []):
            stats["total_functional_requirements"] += len(
                feature.get("functional_requirements", [])
            )
            stats["total_non_functional_requirements"] += len(
                feature.get("non_functional_requirements", [])
            )
            stats["total_actionable_insights"] += len(
                feature.get("actionable_insights", [])
            )

        return stats

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime

        return datetime.now().isoformat()
