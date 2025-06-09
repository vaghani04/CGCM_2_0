from fastapi import Depends
from src.app.usecases.context_gather_usecases.context_gather_usecase import ContextGatherUseCase

class ContextGatherController:
    def __init__(self, context_gather_usecase: ContextGatherUseCase = Depends(ContextGatherUseCase)):
        self.context_gather_usecase = context_gather_usecase

    async def context_gather(self, context_path: str):
        result = await self.context_gather_usecase.execute(context_path)
        return result