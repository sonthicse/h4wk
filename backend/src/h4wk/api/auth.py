"""API đăng nhập, đăng xuất (T7). Đăng nhập sai được ghi vào system audit."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from h4wk.core import audit, auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class Me(BaseModel):
    username: str


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(body: LoginBody, response: Response) -> None:
    if not auth.authenticate(body.username, body.password):
        audit.log(None, f"user:{body.username or '?'}", "auth.login", None, status="error")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username or password")
    token = auth.start_session(body.username)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=int(auth.SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
    )
    audit.log(None, f"user:{body.username}", "auth.login", None)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(auth.SESSION_COOKIE)
    user = auth.session_user(token)
    auth.end_session(token)
    response.delete_cookie(auth.SESSION_COOKIE)
    if user:
        audit.log(None, f"user:{user}", "auth.logout", None)


@router.get("/me")
def me(request: Request) -> Me:
    user = auth.session_user(request.cookies.get(auth.SESSION_COOKIE))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not logged in")
    return Me(username=user)
