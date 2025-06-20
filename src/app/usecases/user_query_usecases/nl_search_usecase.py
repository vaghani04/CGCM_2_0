import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from fastapi import Depends

from src.app.config.settings import settings
from src.app.prompts.query_specific_nl_search_prompts import (
    QUERY_SPECIFIC_NL_SEARCH_SYSTEM_PROMPT,
    QUERY_SPECIFIC_NL_SEARCH_USER_PROMPT,
)
from src.app.services.file_storage_service import FileStorageService
from src.app.services.openai_service import OpenAIService
from src.app.utils.path_utils import get_absolute_path
from src.app.utils.response_parser import parse_response


class NLSearchUsecase:
    def __init__(
        self,
        file_storage_service: FileStorageService = Depends(FileStorageService),
        openai_service: OpenAIService = Depends(OpenAIService),
    ):
        self.file_storage_service = file_storage_service
        self.openai_service = openai_service

    async def get_nl_insights_data(self, data: Dict[str, Any]):
        codebase_path = data["codebase_path"]
        current_git_branch = data["current_git_branch"]
        storage_key = f"{codebase_path}:{current_git_branch}"
        nl_insights = await self.file_storage_service.get_from_file_storage(
            storage_key, file_name="nl_insights.json"
        )
        return nl_insights

    async def query_specific_nl_search(self, data: Dict[str, Any]):
        query = data["query"]
        nl_insights = data["nl_insights"]

        features = nl_insights["features"]

        directory_structure = await self.get_directory_structure(
            data["codebase_path"], depth=5
        )

        user_prompt = QUERY_SPECIFIC_NL_SEARCH_USER_PROMPT.format(
            query=query,
            features=features,
            directory_structure=directory_structure,
        )

        response = await self.openai_service.completions(
            system_prompt=QUERY_SPECIFIC_NL_SEARCH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        parsed_response = parse_response(response)

        with open(
            "intermediate_outputs/nl_search_outputs/nl_search_llm_response.json",
            "w",
        ) as f:
            json.dump(parsed_response, f)

        return parsed_response

    async def nl_search(self, data: Dict[str, Any]):
        nl_insights = await self.get_nl_insights_data(data)

        data["nl_insights"] = nl_insights
        query_specific_nl_context = await self.query_specific_nl_search(data)

        ds = get_absolute_path(
            relative_path=query_specific_nl_context.get(
                "directory", data["codebase_path"]
            ),
            codebase_path=data["codebase_path"],
        )
        directory_structure = await self.get_directory_structure(
            codebase_path=ds, depth=5
        )
        with open(
            "intermediate_outputs/nl_search_outputs/llm_given_directory_structure.txt",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(directory_structure)

        final_response = {}
        if query_specific_nl_context.get("relevant_features", []) != []:
            final_response["relevant_features"] = query_specific_nl_context[
                "relevant_features"
            ]
        else:
            final_response["relevant_features"] = nl_insights.get(
                "features", []
            )

        if directory_structure and len(directory_structure) < 1200:
            final_response["code_hierarchy (in graphical way"] = (
                directory_structure
            )

        final_response["code_hierarchy"] = nl_insights.get("code_hierarchy", "")
        final_response["codebase_flow"] = nl_insights.get("codebase_flow", "")
        final_response["intent_of_codebase"] = nl_insights.get(
            "intent_of_codebase", ""
        )

        return final_response

    async def get_directory_structure(
        self, codebase_path: str, depth: int = 5
    ) -> str:
        """
        Async version of directory structure scanner.
        Returns directory structure as a formatted string.
        Ignores directories from settings.REPO_MAP_EXCLUDED_DIRS
        Only includes .py, .js, .ts files and directories containing them.
        """
        base_path = Path(codebase_path).resolve()

        def is_supported_file(file_path: Path) -> bool:
            """Check if file has supported extension"""
            return (
                file_path.suffix.lower()
                in settings.NL_INSIGHTS_SUPPORTED_EXTENSIONS
            )

        async def traverse(path: Path, current_depth: int) -> list[str]:
            if current_depth > depth:
                return []

            lines = []
            prefix = "│   " * (current_depth - 1) + (
                "├── " if current_depth > 0 else ""
            )

            try:
                items = await asyncio.to_thread(
                    lambda: sorted(path.iterdir(), key=lambda x: x.name)
                )
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

        with open(
            "intermediate_outputs/nl_search_outputs/directory_structure.txt",
            "w",
            encoding="utf-8",
        ) as f:
            f.write("\n".join(structure_lines))

        return "\n".join(structure_lines)
