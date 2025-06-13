from fastapi import Depends
from src.app.usecases.user_query_usecases.user_query_usecase import UserQueryUseCase
from src.app.models.schemas.user_query_schema import UserQueryRequest
class UserQueryController:
    def __init__(self, user_query_usecase: UserQueryUseCase = Depends(UserQueryUseCase)):
        self.user_query_usecase = user_query_usecase

    async def user_query(self, user_query: UserQueryRequest):
        result = await self.user_query_usecase.execute({"query": user_query.query, "codebase_path": user_query.codebase_path})

        
        return result