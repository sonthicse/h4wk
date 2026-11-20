"""Tầng LLM: gửi các mục có dấu hiệu tới tác vụ AI `analysis.classify` và dựng nghi vấn."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from h4wk.ai.gateway import AIGateway
from h4wk.analysis.models import (
    Category,
    Confidence,
    EntityHit,
    Finding,
    ModelRef,
    Severity,
    SourceKind,
    Trigger,
)
from h4wk.collectors.models import Normalized
from h4wk.core.entities import Entity
from h4wk.core.ids import new_ulid
from h4wk.core.types import Contract
from h4wk.media.timeline import Segment, Timeline

log = logging.getLogger(__name__)

BATCH_SIZE = 8
ANALYZER_VERSION = "0.1.0"
PROMPT_PATH = Path(__file__).parent / "prompts" / "classify.md"
NO_VIOLATION = {Category.NEUTRAL, Category.LEGITIMATE_CRITICISM}
SEGMENT_KINDS = {SourceKind.SPEECH, SourceKind.OCR, SourceKind.VISUAL}


class Verdict(Contract):
    """Một kết luận cho một mục."""

    item_id: str
    entity: str
    source_kind: SourceKind
    frame: str | None = None
    category: Category
    severity: Severity
    confidence: Confidence
    quote: str
    reason: str


class Answer(Contract):
    verdicts: list[Verdict]


@dataclass
class Item:
    id: str
    kind: Literal["segment", "title", "description", "thumbnail"]
    segment: Segment | None
    frames: list[str]
    triggers: list[Trigger]
    payload: dict


def _trigger(hit: EntityHit) -> Trigger:
    return Trigger(**hit.model_dump(exclude={"entity"}))


def _segment_payload(segment: Segment) -> dict:
    return {
        "speech": segment.speech,
        "ocr": [o.text for o in segment.ocr],
        "visual": [
            {"frame": v.frame, "description": v.description, "offensive_cues": v.offensive_cues}
            for v in segment.visual
        ],
    }


def build_items(data: Normalized, timeline: Timeline, hits: list[EntityHit]) -> list[Item]:
    """Chọn các mục gửi LLM. Video không có dấu hiệu nào thì không có mục."""
    if not hits:
        return []
    items: list[Item] = []

    def add(kind, segment, frames, triggers, payload):
        items.append(Item(f"i_{len(items) + 1:03d}", kind, segment, frames, triggers, payload))

    segments = timeline.segments
    for index, segment in enumerate(segments):
        triggers = [_trigger(h) for h in hits if h.segment_id == segment.id]
        cues = any(v.offensive_cues for v in segment.visual)
        if not triggers and not cues:
            continue
        before = _segment_payload(segments[index - 1]) if index > 0 else None
        after = _segment_payload(segments[index + 1]) if index + 1 < len(segments) else None
        payload = {
            **_segment_payload(segment),
            "context_before": before,
            "context_after": after,
        }
        add("segment", segment, [v.frame for v in segment.visual], triggers, payload)
    via = {h.via.value for h in hits}
    if data.video:
        if "title" in via:
            add("title", None, [], [Trigger(via="title")], {"text": data.video.title})
        if "description" in via:
            add(
                "description",
                None,
                [],
                [Trigger(via="description")],
                {"text": data.video.description},
            )
    for thumbnail in timeline.thumbnails:
        cues = thumbnail.visual is not None and bool(thumbnail.visual.offensive_cues)
        hit = any(h.via == "thumbnail" and h.frame == thumbnail.file for h in hits)
        if not hit and not cues:
            continue
        payload = {"ocr": [o.text for o in thumbnail.ocr]}
        if thumbnail.visual:
            payload["visual"] = {
                "description": thumbnail.visual.description,
                "offensive_cues": thumbnail.visual.offensive_cues,
            }
        triggers = [Trigger(via="thumbnail", frame=thumbnail.file)] if hit else []
        add("thumbnail", None, [thumbnail.file], triggers, payload)
    return items


def _finding(item: Item, verdict: Verdict, route, timeline: Timeline, run_id: str) -> Finding:
    kind = verdict.source_kind
    frame = None
    if item.kind == "segment":
        if kind not in SEGMENT_KINDS:
            raise ValueError(f"source_kind {kind} is invalid for a segment item")
        if kind == SourceKind.VISUAL:
            frame = verdict.frame if verdict.frame in item.frames else None
            if frame is None and len(item.frames) == 1:
                frame = item.frames[0]
    else:
        kind = SourceKind(item.kind)
        frame = item.frames[0] if item.frames else None
    segment = item.segment
    return Finding(
        id=f"f_{new_ulid()}",
        run_id=run_id,
        video_id=timeline.video_id,
        capture=timeline.capture,
        analyzer="llm",
        analyzer_version=ANALYZER_VERSION,
        model=ModelRef(provider=route.provider, model=route.model),
        source_kind=kind,
        triggers=item.triggers,
        segment_id=segment.id if segment else None,
        start=segment.start if segment else None,
        end=segment.end if segment else None,
        quote=verdict.quote,
        frame=frame,
        entity=verdict.entity,
        category=verdict.category,
        severity=verdict.severity,
        confidence=verdict.confidence,
        reason=verdict.reason,
    )


def classify(
    items: list[Item],
    entities: list[Entity],
    data: Normalized,
    timeline: Timeline,
    hits: list[EntityHit],
    gateway: AIGateway,
    run_id: str,
) -> tuple[list[Finding], list[dict]]:
    """Trả (nghi vấn vi phạm, các bản ghi cho llm.json). GatewayError để người gọi xử lý."""
    system = PROMPT_PATH.read_text(encoding="utf-8")
    known = {e.id for e in entities}
    video = {
        "title": data.video.title if data.video else "",
        "description": data.video.description if data.video else "",
    }
    summary = [{"via": h.via.value, "entity": h.entity} for h in hits]
    findings: list[Finding] = []
    records: list[dict] = []
    for start in range(0, len(items), BATCH_SIZE):
        batch = items[start : start + BATCH_SIZE]
        by_id = {i.id: i for i in batch}
        body = {
            "video": video,
            "entities": [{"id": e.id, "name": e.name, "aliases": e.aliases} for e in entities],
            "video_hits": summary,
            "items": [{"id": i.id, "kind": i.kind, "frames": i.frames, **i.payload} for i in batch],
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(body, ensure_ascii=False)},
        ]
        answer, route = gateway.complete_structured_with_route(
            "analysis.classify", messages, Answer
        )
        for verdict in answer.verdicts:
            item = by_id.get(verdict.item_id)
            if item is None or verdict.entity not in known:
                log.warning("Dropped verdict with unknown item or entity: %s", verdict.item_id)
                continue
            kept = False
            if verdict.category not in NO_VIOLATION:
                try:
                    findings.append(_finding(item, verdict, route, timeline, run_id))
                    kept = True
                except (ValidationError, ValueError) as error:
                    log.warning("Dropped invalid verdict %s: %s", verdict.item_id, error)
            records.append(
                {
                    "item_id": item.id,
                    "verdict": verdict.model_dump(mode="json"),
                    "provider": route.provider,
                    "model": route.model,
                    "kept": kept,
                }
            )
    return findings, records
