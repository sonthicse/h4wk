"""Ứng dụng FastAPI. Router của từng module được gắn vào đây."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from h4wk.api import auth as auth_api
from h4wk.api import entities, jobs, review
from h4wk.core import audit, auth

app = FastAPI(title="h4wk")
app.include_router(auth_api.router)
app.include_router(entities.router)
app.include_router(jobs.router)
app.include_router(review.router)

# Mọi API đều cần đăng nhập, trừ các đường dẫn này (mặc định là chặn).
PUBLIC_PATHS = {"/api/health"}
PUBLIC_PREFIXES = ("/api/auth/",)


@app.middleware("http")
async def _require_login(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    path = request.url.path
    if path.startswith("/api/") and not (path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)):
        username = auth.session_user(request.cookies.get(auth.SESSION_COOKIE))
        if username is None:
            return JSONResponse({"detail": "not logged in"}, status_code=401)
        request.state.username = username
    return await call_next(request)


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.exception_handler(RequestValidationError)
async def _audit_invalid_write(request: Request, exc: RequestValidationError) -> Response:
    """Yêu cầu ghi bị từ chối vì dữ liệu sai cũng phải để lại dòng audit."""
    if request.method in WRITE_METHODS:
        audit.log(
            f"user:{getattr(request.state, 'username', '?')}",
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
