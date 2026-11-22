"""Kết luận theo video từ các nghi vấn đã gộp."""

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from h4wk.analysis.models import (
    NON_VIOLATIONS,
    Confidence,
    Severity,
    VideoVerdict,
)
from h4wk.core.types import VN_TZ


def _rank(finding):
    match = re.fullmatch(r"Jev: \w+ p=(\d\.\d\d)", finding.reason)
    probability = (
        float(match[1]) if match else (0, 0.6, 0.85)[list(Confidence).index(finding.confidence)]
    )
    return list(Severity).index(finding.severity), probability


def decide(findings, run_id, timeline) -> VideoVerdict:
    """Kết luận theo quy tắc, không gọi AI; nghi vấn tĩnh `unverified` không tự đẩy lên `yes`."""
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
        )
    ranked = sorted(violations, key=_rank, reverse=True)
    counts = Counter(f.category for f in violations).most_common()
    severity = max((f.severity for f in violations), key=list(Severity).index)
    sure = any(f.confidence == "highly_likely" for f in violations)
    names = ", ".join(f"{category} ({count})" for category, count in counts)
    return VideoVerdict(
        **base,
        violation="yes" if sure else "uncertain",
        categories=[category for category, _ in counts],
        severity=severity,
        confidence=ranked[0].confidence,
        finding_ids=[f.id for f in ranked[:10]],
        summary=f"{len(violations)} nghi vấn vi phạm; danh mục: {names}; mức cao nhất: {severity}.",
    )


def write(path: Path, decision: VideoVerdict) -> None:
    path.write_text(decision.model_dump_json(indent=2) + "\n", encoding="utf-8")
