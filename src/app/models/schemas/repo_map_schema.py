from pydantic import BaseModel, Field, field_validator
from typing import Optional


class RepoMapGenerationRequest(BaseModel):
    codebase_path: str = Field(
        ..., 
        min_length=1,
        description="Path to the codebase directory",
        example="/path/to/your/codebase"
    )
    
    output_file: Optional[str] = Field(
        default=None,
        description="Optional custom output file name",
        example="custom_repo_map.json"
    )
    
    @field_validator('codebase_path')
    def validate_codebase_path(cls, v):
        if not v or not v.strip():
            raise ValueError("Codebase path cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator('output_file')
    def validate_output_file(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Output file cannot be empty if provided")
        return v.strip() if v else None 