from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable uppercase error code, e.g. VIDEO_NOT_FOUND")
    message: str = Field(..., description="Human-readable safe explanation without sensitive internal details")
    request_id: str = Field(..., description="Traceable unique request identifier")


class ErrorResponse(BaseModel):
    error: ErrorDetail

