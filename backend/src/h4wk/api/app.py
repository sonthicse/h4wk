"""Ứng dụng FastAPI. Router của từng module được gắn vào đây."""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response

from h4wk.api import cases
from h4wk.api.deps import current_actor
from h4wk.core import audit

app = FastAPI(title="h4wk")
app.include_router(cases.router)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.exception_handler(RequestValidationError)
async def _audit_invalid_write(request: Request, exc: RequestValidationError) -> Response:
    """Yêu cầu ghi bị từ chối vì dữ liệu sai cũng phải để lại dòng audit."""
    if request.method in WRITE_METHODS:
        audit.log(
            None,
            current_actor(),
            "request.invalid",
            f"{request.method} {request.url.path}",
            {"errors": len(exc.errors())},
            status="error",
        )
    return await request_validation_exception_handler(request, exc)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Kiểm tra API còn sống."""
    return {"status": "ok"}
