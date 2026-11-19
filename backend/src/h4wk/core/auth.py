"""Tài khoản và phiên đăng nhập (T7). Mật khẩu lưu dạng hash argon2; cookie chỉ chứa token
ngẫu nhiên, database lưu SHA-256 của token."""

import hashlib
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlmodel import Session

from h4wk.core.db import SessionRow, UserRow, as_aware, get_engine
from h4wk.core.types import VN_TZ

SESSION_COOKIE = "h4wk_session"
SESSION_TTL = timedelta(days=7)
_hasher = PasswordHasher()
# Hash giả để người dùng không tồn tại cũng tốn thời gian như sai mật khẩu.
_DUMMY_HASH = _hasher.hash("không-dùng")


def _now() -> datetime:
    return datetime.now(VN_TZ)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(username: str, password: str) -> None:
    if not username or not password:
        raise ValueError("username and password must not be empty")
    with Session(get_engine()) as s:
        if s.get(UserRow, username):
            raise ValueError(f"user {username!r} already exists")
        s.add(UserRow(username=username, password_hash=_hasher.hash(password), created_at=_now()))
        s.commit()


def authenticate(username: str, password: str) -> bool:
    with Session(get_engine()) as s:
        user = s.get(UserRow, username)
    try:
        _hasher.verify(user.password_hash if user else _DUMMY_HASH, password)
    except VerificationError:
        return False
    return user is not None


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
