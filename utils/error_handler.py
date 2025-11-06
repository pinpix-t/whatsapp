"""Centralized error handling for the application"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback

logger = logging.getLogger(__name__)


class WhatsAppAPIError(Exception):
    """Custom exception for WhatsApp API errors"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class LLMError(Exception):
    """Custom exception for LLM errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(Exception):
    """Custom exception for database errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class OrderTrackingError(Exception):
    """Custom exception for order tracking errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


async def whatsapp_api_error_handler(request: Request, exc: WhatsAppAPIError):
    """Handle WhatsApp API errors"""
    logger.error(
        f"WhatsApp API Error: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "whatsapp_api_error",
            "message": exc.message,
            "details": exc.details
        }
    )


async def llm_error_handler(request: Request, exc: LLMError):
    """Handle LLM errors"""
    logger.error(
        f"LLM Error: {exc.message}",
        extra={
            "details": exc.details,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "llm_error",
            "message": "Failed to generate response",
            "details": exc.details
        }
    )


async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle database errors"""
    logger.error(
        f"Database Error: {exc.message}",
        extra={
            "details": exc.details,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "database_error",
            "message": "Database operation failed",
            "details": exc.details
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={"path": request.url.path}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        f"HTTP Exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(
        f"Unexpected Error: {str(exc)}",
        extra={
            "path": request.url.path,
            "traceback": traceback.format_exc()
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred"
        }
    )


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app"""
    app.add_exception_handler(WhatsAppAPIError, whatsapp_api_error_handler)
    app.add_exception_handler(LLMError, llm_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
