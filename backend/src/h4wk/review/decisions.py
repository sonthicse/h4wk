"""Quyết định rà soát. reviews.jsonl là nguồn gốc (chỉ ghi thêm); bảng decisions là chỉ mục.
Ngoài record(), code không đặt trạng thái confirmed ở đâu khác."""

from datetime import datetime

from sqlmodel import Session, select

from h4wk.analysis.models import Finding, ReviewDecision
from h4wk.core.config import data_dir
from h4wk.core.db import DecisionRow, FindingRow, get_engine
from h4wk.core.types import VN_TZ


class NotFound(LookupError):
    pass


def record(finding_id: str, status: str, note: str, by: str) -> ReviewDecision:
    """Ghi một quyết định. Reject thiếu note bị hợp đồng C4 chặn (ValidationError)."""
    with Session(get_engine()) as s:
        row = s.get(FindingRow, finding_id)
        if row is None:
            raise NotFound(finding_id)
        finding = Finding.model_validate_json(row.data)
        decision = ReviewDecision(
            finding_id=finding_id,
            run_id=finding.run_id,
            status=status,  # type: ignore[arg-type]
            by=by,
            at=datetime.now(VN_TZ),
            note=note,
        )
        line = decision.model_dump_json()
        path = data_dir() / "reviews.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        s.add(DecisionRow(finding_id=finding_id, data=line))
        s.commit()
    return decision


def decisions_for(finding_ids: list[str] | None = None) -> dict[str, list[ReviewDecision]]:
    """Các quyết định theo finding_id, mới nhất trước."""
    with Session(get_engine()) as s:
        q = select(DecisionRow).order_by(DecisionRow.id.desc())  # type: ignore[union-attr]
        if finding_ids is not None:
            q = q.where(DecisionRow.finding_id.in_(finding_ids))  # type: ignore[attr-defined]
        rows = s.exec(q).all()
    out: dict[str, list[ReviewDecision]] = {}
    for r in rows:
        out.setdefault(r.finding_id, []).append(ReviewDecision.model_validate_json(r.data))
    return out
