"""Dependency dùng chung của API."""

from fastapi import Request


def current_actor(request: Request) -> str:
    """Người thực hiện thao tác, lấy từ phiên đăng nhập (middleware đã kiểm tra)."""
    return f"user:{request.state.username}"
