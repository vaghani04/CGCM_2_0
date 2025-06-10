from pydantic import BaseModel, Field, field_validator

class UserQueryRequest(BaseModel):
    query: str = Field(..., description="The query to be executed")

    @field_validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()