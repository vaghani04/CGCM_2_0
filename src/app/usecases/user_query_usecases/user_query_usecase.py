from fastapi import Depends
from src.app.usecases.user_query_usecases.user_query_helper import UserQueryHelper
from typing import Dict, Any
class UserQueryUseCase:
    def __init__(self,
                user_query_helper: UserQueryHelper = Depends(UserQueryHelper)):
        self.user_query_helper = user_query_helper

    async def execute(self, user_query: Dict[str, Any]):
        # repo_map_context = await self.user_query_helper.context_from_repo_map(user_query)
        
        # rag_context = await self.user_query_helper.context_from_rag(user_query)

        grep_search_context = await self.user_query_helper.context_from_grep_search(user_query)

        return grep_search_context