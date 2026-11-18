"""Ứng dụng FastAPI. Router của từng module được gắn vào đây."""

from fastapi import FastAPI

app = FastAPI(title="h4wk")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Kiểm tra API còn sống."""
    return {"status": "ok"}
