from typing import Optional
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid

from app.core.logging import logger


class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, message=message, status_code=404)


class UnauthorizedException(AppException):
    def __init__(self, code: str = "UNAUTHORIZED", message: str = "Access denied"):
        super().__init__(code=code, message=message, status_code=403)


class ValidationException(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, message=message, status_code=400)


class PayloadTooLargeException(AppException):
    def __init__(self, code: str = "VIDEO_TOO_LARGE", message: str = "Uploaded file exceeds maximum allowed size"):
        super().__init__(code=code, message=message, status_code=413)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.warning(
        f"AppException: [{exc.code}] {exc.message}",
        extra={"request_id": request_id, "error_code": exc.code}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(
        f"Unhandled exception during request {request_id}",
        extra={"request_id": request_id, "error_code": "INTERNAL_SERVER_ERROR"}
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "request_id": request_id
            }
        }
    )

