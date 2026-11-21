"""Dựng lại index.db từ file trong data/ (SPEC 10.1). Tài khoản, watchlist, video đã biết
và lịch sử job không có file nguồn nên bị mất; đây là hạn chế đã chấp nhận."""

from dataclasses import dataclass

from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session

from h4wk.analysis.models import Finding, ReviewDecision, VideoReviewDecision
from h4wk.core import audit
from h4wk.core.config import data_dir
from h4wk.core.db import (
    DecisionRow,
    EntityRow,
    VideoDecisionRow,
    drop_index,
    finding_row,
    get_engine,
)
from h4wk.core.entities import load_entities

_DECISIONS = TypeAdapter(ReviewDecision | VideoReviewDecision)
_FINDINGS = TypeAdapter(list[Finding])


@dataclass
class ReindexResult:
    entities: int
    videos: int
    findings: int
    decisions: int
    skipped: list[str]  # file hỏng bị bỏ qua, kèm lý do


def _short(e: Exception) -> str:
    return str(e).splitlines()[0] if str(e) else type(e).__name__


def reindex() -> ReindexResult:
    root = data_dir()
    drop_index()
    engine = get_engine()
    skipped: list[str] = []
    entities = findings = decisions = 0
    with Session(engine) as s:
        try:
            items = load_entities()
        except (ValidationError, ValueError) as e:
            skipped.append(f"entities.json: {_short(e)}")
        else:
            for e in items:
                s.add(EntityRow(id=e.id, name=e.name))
            entities = len(items)

        for path in sorted(root.glob("videos/*/derived/*/analysis/*/findings.json")):
            rel = path.relative_to(root).as_posix()
            try:
                found = _FINDINGS.validate_json(path.read_text(encoding="utf-8"))
            except (ValidationError, ValueError) as e:
                skipped.append(f"{rel}: {_short(e)}")
                continue
            for f in found:
                s.add(finding_row(f))
            findings += len(found)
        s.commit()  # nghi vấn phải có trước khi nạp quyết định

        reviews = root / "reviews.jsonl"
        if reviews.is_file():
            for n, line in enumerate(reviews.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = _DECISIONS.validate_json(line)
                except ValidationError as e:
                    skipped.append(f"reviews.jsonl:{n}: {_short(e)}")
                    continue
                if isinstance(d, VideoReviewDecision):
                    s.add(VideoDecisionRow(video_id=d.video_id, run_id=d.run_id, data=line))
                else:
                    s.add(DecisionRow(finding_id=d.finding_id, data=line))
                decisions += 1
        s.commit()

    # đếm giống GET /api/videos; import muộn để core không kéo api (và jobs.queue) khi import
    from h4wk.api.videos import list_videos

    videos = len(list_videos())
    audit.log(
        "system:reindex",
        "index.rebuild",
        None,
        {
            "entities": entities,
            "videos": videos,
            "findings": findings,
            "decisions": decisions,
            "skipped": len(skipped),
        },
    )
    return ReindexResult(entities, videos, findings, decisions, skipped)
