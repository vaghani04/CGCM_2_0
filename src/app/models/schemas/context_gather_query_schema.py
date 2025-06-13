from pydantic import BaseModel, Field, field_validator


class CodebaseContextRequest(BaseModel):
    codebase_path: str = Field(
        ...,
        min_length=1,
        description="Path to the codebase directory",
        example="/path/to/your/codebase",
    )

    @field_validator("codebase_path")
    def validate_codebase_path(cls, v):
        if not v or not v.strip():
            raise ValueError("Codebase path cannot be empty or whitespace only")
        return v.strip()
