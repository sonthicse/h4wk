"""Kết luận theo video từ các nghi vấn đã gộp."""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from h4wk.ai.gateway import GatewayError
from h4wk.analysis.models import (
    NON_VIOLATIONS,
    Confidence,
    ModelRef,
    Severity,
    VerdictAnswer,
    VideoVerdict,
)
from h4wk.core.config_models import AiTask
from h4wk.core.types import VN_TZ

PROMPT = Path(__file__).parent / "prompts" / "video_verdict.md"


def _rank(finding):
    # Jev ghi xác suất danh mục trong lý do; các tầng khác chỉ có mức tin cậy.
    match = re.fullmatch(r"Jev: \w+ p=(\d\.\d\d)", finding.reason)
    probability = (
        float(match[1]) if match else (0, 0.6, 0.85)[list(Confidence).index(finding.confidence)]
    )
    return list(Severity).index(finding.severity), probability


def decide(data, findings, run_id, timeline, gateway) -> tuple[VideoVerdict, str | None]:
    base = dict(
        run_id=run_id, video_id=timeline.video_id, capture=timeline.capture, at=datetime.now(VN_TZ)
    )
    violations = [
        f
        for f in findings
        if f.category not in NON_VIOLATIONS
        and (f.run_id, f.video_id, f.capture) == (run_id, timeline.video_id, timeline.capture)
    ]
    if not violations:
        return VideoVerdict(
            **base, violation="no", confidence="highly_likely", summary="Không có nghi vấn vi phạm."
        ), None

    selected = sorted(violations, key=_rank, reverse=True)[:60]
    fields = {
        "id",
        "source_kind",
        "category",
        "severity",
        "confidence",
        "reason",
        "start",
        "entity",
    }
    body = {
        "title": data.video.title if data.video else "",
        "description": data.video.description if data.video else "",
        "channel": data.channel.title
        if data.channel
        else (data.video.channel_id if data.video else ""),
        "total_findings": len(violations),
        "findings": [
            f.model_dump(mode="json", include=fields) | {"quote": f.quote[:300]} for f in selected
        ],
    }
    messages = [
        {"role": "system", "content": PROMPT.read_text(encoding="utf-8")},
        {"role": "user", "content": json.dumps(body, ensure_ascii=False)},
    ]
    try:
        answer, route = gateway.complete_structured_with_route(
            AiTask.VIDEO_VERDICT, messages, VerdictAnswer
        )
        allowed = {f.id for f in selected}
        ids = list(dict.fromkeys(i for i in answer.finding_ids if i in allowed))[:10]
        return VideoVerdict(
            **base,
            **(answer.model_dump() | {"finding_ids": ids}),
            model=ModelRef(provider=route.provider, model=route.model),
        ), None
    except (GatewayError, ValidationError) as error:
        short = (str(error).partition("\n")[0] or type(error).__name__)[:180]
        return VideoVerdict(
            **base,
            violation="uncertain",
            confidence="unverified",
            categories=[c for c, _ in Counter(f.category for f in violations).most_common()],
            severity=max((f.severity for f in violations), key=list(Severity).index),
            finding_ids=[f.id for f in violations],
            summary=f"Chưa có kết luận tự động: {short}",
        ), f"analysis.video_verdict: {error}"


def write(path: Path, decision: VideoVerdict) -> None:
    path.write_text(decision.model_dump_json(indent=2) + "\n", encoding="utf-8")
