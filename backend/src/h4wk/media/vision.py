"""Mô tả các khung và thumbnail, ghi nhận tuyến AI thực sự trả lời."""

import logging
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from h4wk.ai.gateway import AIGateway, GatewayError
from h4wk.core.types import Contract
from h4wk.media.files import atomic_output
from h4wk.media.timeline import Visual

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).parent / "prompts" / "vision.md"


class Description(Contract):
    description: str
    offensive_cues: list[str]


class CachedVisual(Visual):
    image_sha256: str
    config_sha256: str


def describe_images(images: list[tuple[str, Path]], output: Path) -> dict[str, Visual]:
    gateway = AIGateway()

    if images and not gateway.config_path.exists():
        # Không gọi gateway và không ghi vision.json để giữ nguyên cache cũ.
        logger.warning("Skipping image descriptions: %s not found", gateway.config_path)
        return {}
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if images else ""
    config_hash = ""
    if images:
        prompt_digest = sha256(prompt.encode("utf-8")).digest()
        config_hash = sha256(gateway.config_path.read_bytes() + prompt_digest).hexdigest()
    adapter = TypeAdapter(dict[str, CachedVisual])
    cached = {}
    if output.exists():
        try:
            cached = adapter.validate_json(output.read_bytes())
        except ValidationError:
            pass

    def describe(item: tuple[str, Path]) -> tuple[str, CachedVisual | None]:
        file, path = item
        image = path.read_bytes()
        digest = sha256(image).hexdigest()
        if (
            file in cached
            and cached[file].image_sha256 == digest
            and cached[file].config_sha256 == config_hash
        ):
            return file, cached[file]
        try:
            answer, route = gateway.describe_image_with_route(
                "media.vision",
                image,
                prompt,
                Description,
            )
        except GatewayError as error:
            # Bỏ ảnh lỗi, không vào cache để lần chạy sau thử lại đúng ảnh này.
            logger.warning("Could not describe %s: %s", file, error)
            return file, None
        return file, CachedVisual(
            **answer.model_dump(),
            image_sha256=digest,
            config_sha256=config_hash,
            provider=route.provider,
            model=route.model,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(describe, images))
    results = {file: row for file, row in rows if row is not None}
    # Ảnh lỗi giữ lại dòng cache cũ (nếu có) để không mất dữ liệu đã có.
    failed = [file for file, row in rows if row is None]
    stored = {**{f: cached[f] for f in failed if f in cached}, **results}
    if stored != cached or not output.exists():
        with atomic_output(output) as temporary:
            temporary.write_bytes(adapter.dump_json(stored, indent=2))
    return {
        file: Visual(**row.model_dump(exclude={"image_sha256", "config_sha256"}))
        for file, row in results.items()
    }
