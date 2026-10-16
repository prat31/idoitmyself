from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for expected application errors, rendered as a JSON error body."""

    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class InvalidRequestError(AppError):
    status_code = 422
    code = "invalid_request"


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
