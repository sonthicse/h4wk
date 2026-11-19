"""Định tuyến, kiểm tra kết quả và ghi nhật ký các lần gọi AI."""

import json
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from threading import Lock
from time import perf_counter

from dotenv import dotenv_values
from pydantic import BaseModel, ValidationError

from h4wk.ai.base import Message, Provider, ProviderError, ProviderReply, ProviderRequest
from h4wk.ai.config import ai_config_path, load_ai_config
from h4wk.ai.providers import make_provider
from h4wk.core.config import REPO_ROOT, data_dir
from h4wk.core.config_models import AiTask, Route
from h4wk.core.types import VN_TZ

# Một request đang chạy cho mỗi nhà cung cấp trong tiến trình worker.
_provider_locks: dict[str, Lock] = {}


class GatewayError(RuntimeError):
    """Không còn tuyến nào trả về kết quả hợp lệ."""


class AIGateway:
    def __init__(
        self,
        providers: Mapping[str, Provider] | None = None,
        *,
        config_path: Path | None = None,
        log_dir: Path | None = None,
    ):
        self.providers = providers
        self.config_path = config_path or ai_config_path()
        self.log_path = (data_dir() if log_dir is None else log_dir) / "ai_calls.jsonl"

    def complete_structured[M: BaseModel](
        self,
        task: AiTask | str,
        messages: list[Message],
        schema: type[M],
    ) -> M:
        answer, _ = self._run(AiTask(task), messages, schema, image=None)
        return answer

    def describe_image[M: BaseModel](
        self,
        task: AiTask | str,
        image: bytes,
        prompt: str,
        schema: type[M],
    ) -> M:
        answer, _ = self.describe_image_with_route(task, image, prompt, schema)
        return answer

    def describe_image_with_route[M: BaseModel](
        self, task: AiTask | str, image: bytes, prompt: str, schema: type[M]
    ) -> tuple[M, Route]:
        return self._run(AiTask(task), [{"role": "user", "content": prompt}], schema, image)

    def _run[M: BaseModel](
        self,
        task: AiTask,
        messages: list[Message],
        schema: type[M],
        image: bytes | None,
    ) -> tuple[M, Route]:
        config = load_ai_config(self.config_path)
        routes = config.tasks.get(task)
        if not routes:
            raise GatewayError(f"{task}: no route configured")

        json_schema = schema.model_json_schema()
        last_error = None
        unavailable: list[str] = []
        keys = {**dotenv_values(REPO_ROOT / ".env"), **os.environ} if self.providers is None else {}
        for route in routes:
            provider = (
                make_provider(route.provider, config.providers[route.provider], keys)
                if self.providers is None
                else self.providers.get(route.provider)
            )
            caps = config.providers[route.provider].models[route.model]
            if provider is None:
                unavailable.append(f"{route.provider}/{route.model}: missing API key")
                continue
            if image is not None and not caps.vision:
                unavailable.append(f"{route.provider}/{route.model}: cannot read images")
                continue
            history = list(messages)
            for attempt in range(3):
                request = ProviderRequest(route.model, history, json_schema, caps.structured, image)
                reply = None
                try:
                    with _provider_locks.setdefault(route.provider, Lock()):
                        start = perf_counter()
                        reply = provider.complete(request)
                except ProviderError as error:
                    self._log(task, route, start, "provider_error", None)
                    last_error = error
                    break

                try:
                    answer = schema.model_validate_json(reply.text)
                except ValidationError as error:
                    self._log(task, route, start, "invalid_output", reply)
                    last_error = error
                    if attempt < 2:
                        history = [
                            *history,
                            {"role": "assistant", "content": reply.text},
                            {
                                "role": "user",
                                "content": "Sửa JSON theo lỗi sau:\n"
                                + error.json(include_input=False, include_url=False),
                            },
                        ]
                else:
                    self._log(task, route, start, "ok", reply)
                    return answer, route
        if last_error is None:
            raise GatewayError(f"{task}: no AI provider available ({'; '.join(unavailable)})")
        raise GatewayError(f"{task}: no valid result ({last_error})") from last_error

    def _log(
        self,
        task: AiTask,
        route: Route,
        start: float,
        status: str,
        reply: ProviderReply | None,
    ) -> None:
        record = {
            "at": datetime.now(VN_TZ).isoformat(),
            "task": task,
            "provider": route.provider,
            "model": route.model,
            "status": status,
            "latency_ms": (perf_counter() - start) * 1000,
            "input_tokens": reply.input_tokens if reply else None,
            "output_tokens": reply.output_tokens if reply else None,
            "cost_usd": reply.cost_usd if reply else None,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
