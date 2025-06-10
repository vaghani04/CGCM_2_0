from fastapi import Depends
from src.app.usecases.user_query_usecases.user_query_helper import UserQueryHelper

class UserQueryUseCase:
    def __init__(self,
                user_query_helper: UserQueryHelper = Depends(UserQueryHelper)):
        self.user_query_helper = user_query_helper

    async def execute(self, query: str):
        context = await self.user_query_helper.context_from_repo_map(query)
        return context