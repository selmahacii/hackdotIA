from typing import Any

from fastapi import HTTPException, status


class AppError(Exception):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DatabaseUnavailableError(HTTPException):
    def __init__(self, detail: str = "Database connection unavailable") -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
