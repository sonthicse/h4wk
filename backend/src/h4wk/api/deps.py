from fastapi import Request


def current_actor(request: Request) -> str:
    return f"user:{request.state.username}"
