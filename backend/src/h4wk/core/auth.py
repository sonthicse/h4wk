"""Đăng nhập một tài khoản duy nhất. Tên và mật khẩu lấy từ `USERNAME`, `PASSWORD` trong file
.env. Cookie chỉ chứa token ngẫu nhiên, database lưu SHA-256 của token."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session

from h4wk.core import config
from h4wk.core.db import SessionRow, as_aware, get_engine
from h4wk.core.types import VN_TZ

SESSION_COOKIE = "session"
SESSION_TTL = timedelta(days=7)
USERNAME, PASSWORD = "USERNAME", "PASSWORD"


def _now() -> datetime:
    return datetime.now(VN_TZ)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def account() -> tuple[str, str]:
    """Tên và mật khẩu của tài khoản duy nhất; thiếu thì báo lỗi rõ."""
    env = config.dotenv()
    username, password = env.get(USERNAME), env.get(PASSWORD)
    if not username or not password:
        raise RuntimeError(f"set {USERNAME} and {PASSWORD} in .env")
    return username, password


def authenticate(username: str, password: str) -> bool:
    expected_user, expected_password = account()
    # So sánh thời gian cố định, kiểm cả hai vế để thời gian không lộ vế nào sai.
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    return user_ok and password_ok


def start_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    with Session(get_engine()) as s:
        s.add(
            SessionRow(
                token_hash=_token_hash(token), username=username, expires_at=_now() + SESSION_TTL
            )
        )
        s.commit()
    return token


def session_user(token: str | None) -> str | None:
    """Username của phiên còn hạn, hoặc None."""
    if not token:
        return None
    with Session(get_engine()) as s:
        row = s.get(SessionRow, _token_hash(token))
        if row is None:
            return None
        if as_aware(row.expires_at) <= _now():
            s.delete(row)
            s.commit()
            return None
        return row.username


def end_session(token: str | None) -> None:
    if not token:
        return
    with Session(get_engine()) as s:
        row = s.get(SessionRow, _token_hash(token))
        if row:
            s.delete(row)
            s.commit()
