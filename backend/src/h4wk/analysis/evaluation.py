"""Công cụ lấy mẫu và chấm điểm để so sánh tầng tĩnh với tầng LLM (T38)."""

import random
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter

from h4wk.analysis.models import EntityHit, Finding
from h4wk.analysis.runner import _slot, analyze
from h4wk.collectors.models import Normalized
from h4wk.core.entities import load_entities
from h4wk.media.timeline import Timeline

_HITS = TypeAdapter(list[EntityHit])
_FINDINGS = TypeAdapter(list[Finding])


@dataclass
class Unit:
    """Một mục cần gán nhãn: (vị trí, đối tượng) trong một bản thu."""

    video_id: str
    capture: str
    run_id: str
    place: str
    kind: str  # segment | comment | title | description | thumbnail
    entity: str
    text: str
    static: bool
    llm: bool
    unit_id: str = ""


def place_of(
    hit: EntityHit, thumbnails: set[str] | frozenset[str] = frozenset()
) -> tuple[str, str]:
    """Trả (vị trí, loại mục) theo cùng quy tắc với `runner._slot`.

    `thumbnails` là tên các file thumbnail của timeline; frame khác (keyframe không thuộc
    đoạn nào) có loại "frame"."""
    if hit.comment_id:
        return hit.comment_id, "comment"
    if hit.segment_id:
        return hit.segment_id, "segment"
    via = hit.via.value
    if via in ("thumbnail", "ref_image") and hit.frame:
        return hit.frame, "thumbnail" if hit.frame in thumbnails else "frame"
    return via, via


def _finding_kind(finding: Finding) -> str:
    if finding.comment_id:
        return "comment"
    if finding.segment_id:
        return "segment"
    return finding.source_kind.value


def _text(kind: str, place: str, data: Normalized, timeline: Timeline) -> str:
    if kind == "comment":
        by_id = {c.id: c for c in data.comments}
        comment = by_id.get(place)
        if comment is None:
            return ""
        parent = by_id.get(comment.parent_id) if comment.parent_id else None
        return comment.text + (f"\nReply to: {parent.text}" if parent else "")
    if kind == "title":
        return data.video.title if data.video else ""
    if kind == "description":
        return data.video.description if data.video else ""
    if kind == "segment":
        segment = next((s for s in timeline.segments if s.id == place), None)
        if segment is None:
            return ""
        parts = [segment.speech]
        parts += [f"OCR: {o.text}" for o in segment.ocr]
        for v in segment.visual:
            cues = f" ({', '.join(v.offensive_cues)})" if v.offensive_cues else ""
            parts.append(f"Visual: {v.description}{cues}")
        return "\n".join(p for p in parts if p)
    if kind == "frame":
        for segment in timeline.segments:
            for v in segment.visual:
                if v.frame == place:
                    return f"Visual: {v.description}"
        return f"(keyframe {place})"
    thumbnail = next((t for t in timeline.thumbnails if t.file == place), None)
    if thumbnail is None:
        return ""
    parts = [f"OCR: {o.text}" for o in thumbnail.ocr]
    if thumbnail.visual:
        parts.append(f"Visual: {thumbnail.visual.description}")
    return "\n".join(parts)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_units(root: Path) -> list[Unit]:
    """Gom các mục từ mọi bản thu có run mới nhất đã chạy LLM (có llm.json)."""
    entities = load_entities()
    units: list[Unit] = []
    for derived in sorted(root.glob("videos/*/derived/*")):
        runs = sorted(p for p in (derived / "analysis").glob("*") if p.is_dir())
        if not runs or not (runs[-1] / "llm.json").is_file():
            continue
        run = runs[-1]
        video_id, capture = derived.parent.parent.name, derived.name
        normalized = root / "videos" / video_id / "captures" / capture / "normalized.json"
        data = Normalized.model_validate_json(_read(normalized))
        timeline = Timeline.model_validate_json(_read(derived / "timeline.json"))
        hits = _HITS.validate_json(_read(run / "hits.json"))
        findings = _FINDINGS.validate_json(_read(run / "findings.json"))
        llm_slots = {_slot(f) for f in findings if f.analyzer == "llm"}
        with tempfile.TemporaryDirectory() as tmp:
            _, static_findings, _ = analyze(
                data, timeline, entities, None, "r_eval", Path(tmp), gateway=None
            )
        static_slots = {_slot(f) for f in static_findings}
        thumbnails = {t.file for t in timeline.thumbnails}
        pending: list[tuple[str, str, str]] = []  # (place, kind, entity)
        for hit in hits:
            pending.append((*place_of(hit, thumbnails), hit.entity))
        # Nghi vấn không có hit cùng (vị trí, đối tượng): đoạn chỉ có offensive_cues,
        # hoặc LLM kết luận về đối tượng khác với hit.
        for finding in [*static_findings, *(f for f in findings if f.analyzer == "llm")]:
            place, entity = _slot(finding)
            pending.append((place, _finding_kind(finding), entity))
        seen: set[tuple[str, str]] = set()
        for place, kind, entity in pending:
            slot = (place, entity)
            if slot in seen:
                continue
            seen.add(slot)
            units.append(
                Unit(
                    video_id=video_id,
                    capture=capture,
                    run_id=run.name,
                    place=place,
                    kind=kind,
                    entity=entity,
                    text=_text(kind, place, data, timeline),
                    static=slot in static_slots,
                    llm=slot in llm_slots,
                )
            )
    return units


def sample(units: list[Unit], n: int = 50, seed: int = 0) -> list[Unit]:
    """Lấy mọi mục dương (tối đa n//2), phần còn lại lấy ngẫu nhiên từ mục âm."""
    rng = random.Random(seed)
    positives = [u for u in units if u.static or u.llm]
    negatives = [u for u in units if not (u.static or u.llm)]
    if len(positives) > n // 2:
        positives = rng.sample(positives, n // 2)
    negatives = rng.sample(negatives, min(len(negatives), n - len(positives)))
    chosen = sorted(positives + negatives, key=lambda u: (u.video_id, u.place))
    for i, unit in enumerate(chosen, 1):
        unit.unit_id = f"u_{i:03d}"
    return chosen


def score(rows: list[dict]) -> dict[str, dict]:
    """Precision/recall của từng tầng trên các dòng đã gán nhãn (label rỗng thì bỏ qua)."""
    labelled = [r for r in rows if r.get("label") in ("1", "0")]
    result: dict[str, dict] = {}
    for layer in ("static", "llm"):
        tp = fp = fn = tn = 0
        for r in labelled:
            truth, pred = r["label"] == "1", r[layer] == "1"
            if pred and truth:
                tp += 1
            elif pred:
                fp += 1
            elif truth:
                fn += 1
            else:
                tn += 1
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        if precision is None or recall is None:
            f1 = None
        else:
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        result[layer] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1, "n": len(labelled),
        }  # fmt: skip
    return result


def _fmt(value: float | None) -> str:
    return "–" if value is None else f"{value:.2f}"


def markdown_table(scores: dict[str, dict]) -> str:
    lines = [
        "| Tầng | n | TP | FP | FN | TN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for layer, s in scores.items():
        lines.append(
            f"| {layer} | {s['n']} | {s['tp']} | {s['fp']} | {s['fn']} | {s['tn']} "
            f"| {_fmt(s['precision'])} | {_fmt(s['recall'])} | {_fmt(s['f1'])} |"
        )
    return "\n".join(lines)
