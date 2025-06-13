from pydantic import BaseModel, Field, field_validator

class UserQueryRequest(BaseModel):
    query: str = Field(..., description="The query to be executed")
    codebase_path: str = Field(..., description="Path to the codebase to analyze")

    @field_validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()
        
    @field_validator('codebase_path')
    def validate_codebase_path(cls, v):
        if not v or not v.strip():
            raise ValueError("Codebase path cannot be empty or whitespace only")
        return v.strip()