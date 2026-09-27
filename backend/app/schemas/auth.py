from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import strip_non_empty_str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)

    @classmethod
    def validate_username(cls, v: str) -> str:
        return strip_non_empty_str(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=28800, description="Token validity duration in seconds")
