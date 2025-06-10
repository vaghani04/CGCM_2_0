from fastapi import Depends
from src.app.usecases.user_query_usecases.user_query_usecase import UserQueryUseCase

class UserQueryController:
    def __init__(self, user_query_usecase: UserQueryUseCase = Depends(UserQueryUseCase)):
        self.user_query_usecase = user_query_usecase

    async def user_query(self, query: str):
        result = await self.user_query_usecase.execute(query)

        
        return result