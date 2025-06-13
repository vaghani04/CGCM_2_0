from fastapi import HTTPException
from pathlib import Path
async def create_intermediate_output_directories():
    """
    Create all required intermediate output directories if they don't exist
    """
    try:
        # List of all intermediate output directories used in the codebase
        directories = [
            "intermediate_outputs",
            "intermediate_outputs/nl_search_outputs",
            "intermediate_outputs/repo_map_search_outputs", 
            "intermediate_outputs/grep_search_outputs",
            "intermediate_outputs/rag_search_outputs",
            "intermediate_outputs/nl_context_gather_outputs",
            "intermediate_outputs/rag_context_gather_outputs"
        ]
        
        # Create each directory if it doesn't exist
        for directory in directories:
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating intermediate output directories: {str(e)}"
        )