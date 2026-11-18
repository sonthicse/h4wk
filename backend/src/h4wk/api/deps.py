"""Dependency dùng chung của API."""


def current_actor() -> str:
    """Người thực hiện thao tác. Tạm thời cố định; T7 lấy từ session đăng nhập."""
    return "user:anonymous"
