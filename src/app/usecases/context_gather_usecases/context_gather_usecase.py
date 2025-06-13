from fastapi import Depends
from src.app.usecases.context_gather_usecases.context_gather_helper import ContextGatherHelper
from src.app.utils.generate_dirs_for_ir import create_intermediate_output_directories

class ContextGatherUseCase:
    def __init__(
        self,
        context_gather_helper: ContextGatherHelper = Depends(ContextGatherHelper),
    ):
        self.context_gather_helper = context_gather_helper
        
    async def execute(self, codebase_path: str):
        """
        Execute the context gathering process up to MongoDB storage
        
        Args:
            codebase_path: Path to the codebase
            
        Returns:
            Dictionary with statistics and results
        """

        await create_intermediate_output_directories()
        
        # Get git branch name
        git_branch_name = await self.context_gather_helper.get_current_branch_name(codebase_path)
        # return git_branch_name

        stats = await self.context_gather_helper.chunking_and_storage(codebase_path, git_branch_name)

        return stats