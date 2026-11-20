"""Phân tích bình luận bằng LLM, theo lô, qua tác vụ AI `analysis.classify_comment`."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from h4wk.ai.gateway import AIGateway
from h4wk.analysis.llm import ANALYZER_VERSION, NO_VIOLATION
from h4wk.analysis.models import (
    Category,
    Confidence,
    EntityHit,
    Finding,
    ModelRef,
    Severity,
    Trigger,
)
from h4wk.collectors.models import Comment, Normalized
from h4wk.core.config_models import CommentSettings
from h4wk.core.entities import Entity
from h4wk.core.ids import new_ulid
from h4wk.core.types import Contract
from h4wk.media.timeline import Timeline

log = logging.getLogger(__name__)

TASK = "analysis.classify_comment"
PROMPT_PATH = Path(__file__).parent / "prompts" / "classify_comment.md"


class CommentVerdict(Contract):
    comment_id: str
    entity: str
    category: Category
    severity: Severity
    confidence: Confidence
    quote: str
    reason: str


class CommentAnswer(Contract):
    verdicts: list[CommentVerdict]


def select_comments(
    data: Normalized, hits: list[EntityHit], settings: CommentSettings
) -> list[Comment]:
    """Comment có dấu hiệu tên, theo thứ tự trong video, cắt theo max_per_video."""
    hit_ids = {h.comment_id for h in hits if h.via == "comment"}
    selected = []
    seen = set()
    for comment in data.comments:
        if comment.id in hit_ids and comment.id not in seen:
            seen.add(comment.id)
            selected.append(comment)
    if settings.max_per_video is not None:
        selected = selected[: settings.max_per_video]
    return selected


def classify_comments(
    comments: list[Comment],
    entities: list[Entity],
    data: Normalized,
    hits: list[EntityHit],
    gateway: AIGateway,
    run_id: str,
    timeline: Timeline,
    settings: CommentSettings,
) -> tuple[list[Finding], list[dict]]:
    """Trả (nghi vấn vi phạm, các bản ghi cho llm.json). GatewayError để người gọi xử lý."""
    system = PROMPT_PATH.read_text(encoding="utf-8")
    known = {e.id for e in entities}
    texts = {c.id: c.text for c in data.comments}
    video = {
        "title": data.video.title if data.video else "",
        "description": data.video.description if data.video else "",
    }
    findings: list[Finding] = []
    records: list[dict] = []
    for start in range(0, len(comments), settings.batch_size):
        batch = comments[start : start + settings.batch_size]
        ids = {c.id for c in batch}
        body = {
            "video": video,
            "entities": [{"id": e.id, "name": e.name, "aliases": e.aliases} for e in entities],
            "comments": [
                {"id": c.id, "text": c.text, "parent_text": texts.get(c.parent_id or "")}
                for c in batch
            ],
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(body, ensure_ascii=False)},
        ]
        answer, route = gateway.complete_structured_with_route(TASK, messages, CommentAnswer)
        for verdict in answer.verdicts:
            record = {
                "task": TASK,
                "item_id": verdict.comment_id,
                "verdict": verdict.model_dump(mode="json"),
                "provider": route.provider,
                "model": route.model,
                "kept": False,
            }
            records.append(record)
            if verdict.comment_id not in ids or verdict.entity not in known:
                record["error"] = "unknown comment or entity"
                log.warning(
                    "Dropped verdict with unknown comment or entity: %s", verdict.comment_id
                )
                continue
            if verdict.category in NO_VIOLATION:
                continue
            try:
                findings.append(
                    Finding(
                        id=f"f_{new_ulid()}",
                        run_id=run_id,
                        video_id=timeline.video_id,
                        capture=timeline.capture,
                        analyzer="llm",
                        analyzer_version=ANALYZER_VERSION,
                        model=ModelRef(provider=route.provider, model=route.model),
                        source_kind="comment",
                        triggers=[Trigger(via="comment", comment_id=verdict.comment_id)],
                        comment_id=verdict.comment_id,
                        quote=verdict.quote,
                        entity=verdict.entity,
                        category=verdict.category,
                        severity=verdict.severity,
                        confidence=verdict.confidence,
                        reason=verdict.reason,
                    )
                )
                record["kept"] = True
            except (ValidationError, ValueError) as error:
                log.warning("Dropped invalid verdict %s: %s", verdict.comment_id, error)
                record["error"] = str(error)
    return findings, records
