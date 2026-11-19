"""Dựng lại index.db từ file trong data/ (SPEC 10.1). Tài khoản, watchlist, video đã biết
và lịch sử job không có file nguồn nên bị mất; đây là hạn chế đã chấp nhận."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session

from h4wk.analysis.models import Finding, ReviewDecision
from h4wk.core import audit
from h4wk.core.config import data_dir
from h4wk.core.db import DecisionRow, EntityRow, FindingRow, drop_index, get_engine
from h4wk.core.entities import Entity

_ENTITIES = TypeAdapter(list[Entity])
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


def reindex(root: Path | None = None) -> ReindexResult:
    root = root or data_dir()
    drop_index(root)
    engine = get_engine(root)
    skipped: list[str] = []
    entities = findings = decisions = 0
    with Session(engine) as s:
        entities_file = root / "entities.json"
        if entities_file.is_file():
            try:
                items = _ENTITIES.validate_json(entities_file.read_text(encoding="utf-8"))
            except (ValidationError, ValueError) as e:
                skipped.append(f"entities.json: {_short(e)}")
            else:
                for e in items:
                    s.add(EntityRow(id=e.id, name=e.name))
                entities = len(items)

        videos_dir = root / "videos"
        video_dirs = (
            [d for d in sorted(videos_dir.iterdir()) if d.is_dir()] if (videos_dir.is_dir()) else []
        )
        for path in sorted(videos_dir.glob("*/derived/*/analysis/*/findings.json")):
            rel = path.relative_to(root).as_posix()
            try:
                items = _FINDINGS.validate_json(path.read_text(encoding="utf-8"))
            except (ValidationError, ValueError) as e:
                skipped.append(f"{rel}: {_short(e)}")
                continue
            for f in items:
                s.add(
                    FindingRow(
                        id=f.id,
                        video_id=f.video_id,
                        capture=f.capture,
                        run_id=f.run_id,
                        data=f.model_dump_json(),
                    )
                )
            findings += len(items)
        s.commit()  # nghi vấn phải có trước khi nạp quyết định

        reviews = root / "reviews.jsonl"
        if reviews.is_file():
            lines = reviews.read_text(encoding="utf-8").splitlines()
            for n, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = ReviewDecision.model_validate_json(line)
                except ValidationError as e:
                    skipped.append(f"reviews.jsonl:{n}: {_short(e)}")
                    continue
                s.add(DecisionRow(finding_id=d.finding_id, data=line))
                decisions += 1
        s.commit()

    result = ReindexResult(entities, len(video_dirs), findings, decisions, skipped)
    audit.log(
        "system:reindex",
        "index.rebuild",
        None,
        {
            "entities": entities,
            "videos": len(video_dirs),
            "findings": findings,
            "decisions": decisions,
            "skipped": len(skipped),
        },
    )
    return result
