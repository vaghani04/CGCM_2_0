from fastapi import Depends
from src.app.usecases.context_gather_usecases.context_gather_helper import ContextGatherHelper

class ContextGatherUseCase:
    def __init__(self, context_gather_helper: ContextGatherHelper = Depends(ContextGatherHelper)):
        self.context_gather_helper = context_gather_helper

    async def execute(self, codebase_path: str):
        
        return await self.context_gather_helper.get_current_branch_name(codebase_path)
        return "HI"