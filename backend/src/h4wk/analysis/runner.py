"""Phân tích tĩnh văn bản theo các đối tượng cần bảo vệ."""

import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from h4wk.analysis import jev
from h4wk.analysis.models import (
    Confidence,
    EntityHit,
    Finding,
    Occurrence,
    Severity,
    SourceKind,
    Trigger,
)
from h4wk.analysis.normalize import matches_name, normalize
from h4wk.analysis.static import LexiconEntry, find_insult, load_lexicon
from h4wk.collectors.models import Normalized
from h4wk.core.entities import Entity
from h4wk.core.ids import new_ulid
from h4wk.media.timeline import Timeline


def analyze(
    data: Normalized,
    timeline: Timeline,
    entities: list[Entity],
    lexicon: list[LexiconEntry] | None,
    run_id: str,
    output_dir: Path,
    extra_hits: list[EntityHit] | None = None,
    use_jev: bool = False,
    derived_dir: Path | None = None,
    capture_dir: Path | None = None,
) -> tuple[list[EntityHit], list[Finding], str | None]:
    if lexicon is None:
        lexicon = load_lexicon()
    hits: list[EntityHit] = []
    findings: list[Finding] = []

    def scan(text, via, segment=None, comment_id=None, frame=None, bbox=None):
        for entity in entities:
            if not matches_name(text, [entity.name, *entity.aliases], entity.abbreviations):
                continue
            hit = EntityHit(
                entity=entity.id,
                via=via,
                segment_id=segment.id if segment else None,
                comment_id=comment_id,
                frame=frame,
                bbox=bbox,
            )
            hits.append(hit)
            entry = find_insult(text, lexicon)
            if entry is not None:
                findings.append(
                    Finding(
                        id=f"f_{new_ulid()}",
                        run_id=run_id,
                        video_id=timeline.video_id,
                        capture=timeline.capture,
                        analyzer="static",
                        analyzer_version="0.1.0",
                        source_kind=via,
                        triggers=[Trigger(**hit.model_dump(exclude={"entity"}))],
                        segment_id=hit.segment_id,
                        comment_id=comment_id,
                        start=segment.start if segment else None,
                        end=segment.end if segment else None,
                        quote=text,
                        frame=frame,
                        bbox=bbox,
                        entity=entity.id,
                        category=entry.category,
                        severity="medium",
                        confidence="unverified",
                        reason=f"Từ điển nhóm '{entry.group}': '{entry.phrase}'.",
                    )
                )

    if data.video:
        scan(data.video.title, "title")
        scan(data.video.description, "description")
    for segment in timeline.segments:
        scan(segment.speech, "speech", segment)
        for item in segment.ocr:
            scan(item.text, "ocr", segment, frame=item.frame, bbox=item.bbox)
    for thumbnail in timeline.thumbnails:
        for item in thumbnail.ocr:
            scan(item.text, "thumbnail", frame=thumbnail.file, bbox=item.bbox)
    for comment in data.comments:
        scan(comment.text, "comment", comment_id=comment.id)

    # Dấu hiệu ảnh mẫu (T40) không có văn bản nên không qua tầng tĩnh; gộp trước khi chọn mục.
    hits.extend(extra_hits or [])

    errors: list[str] = []
    records: list[dict] | None = None

    def merge(part_findings, part_records):
        nonlocal findings, records
        records = (records or []) + part_records

        def slot(f):
            # Giữ riêng nghi vấn lời nói và hình trong cùng đoạn.
            return _slot(f), f.source_kind == SourceKind.SPEECH

        replaced = {slot(f) for f in part_findings}
        findings = [f for f in findings if f.analyzer != "static" or slot(f) not in replaced]
        findings.extend(part_findings)

    if use_jev:
        part_findings, part_records, error = jev.classify(
            data,
            timeline,
            entities,
            hits,
            run_id,
            derived_dir=derived_dir,
            capture_dir=capture_dir,
        )
        merge(part_findings, part_records)
        if error:
            errors.append(error)
    jev_error = "; ".join(errors) or None
    references = [data.video.title, data.video.description] if data.video else []
    references += [segment.speech for segment in timeline.segments]
    findings = group_repeats(findings, references)

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, items in (("hits.json", hits), ("findings.json", findings)):
        content = [item.model_dump(mode="json", by_alias=True) for item in items]
        _write(output_dir / filename, content)
    if records is not None:
        _write(output_dir / "jev.json", records)
    return hits, findings, jev_error


def _slot(finding: Finding) -> tuple[str, str]:
    """Mục chứa nghi vấn (cộng đối tượng): segment, file thumbnail, hoặc loại nguồn."""
    if finding.comment_id:
        place = finding.comment_id
    elif finding.segment_id:
        place = finding.segment_id
    elif finding.source_kind == "thumbnail" and finding.frame:
        place = finding.frame
    else:
        place = finding.source_kind.value
    return place, finding.entity


def _write(path: Path, content: list) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slots(finding: Finding) -> list[tuple[str, str]]:
    """Mọi mục chứa nghi vấn: mỗi chỗ xuất hiện một mục (nghi vấn đã gộp), còn lại như `_slot`."""
    if finding.occurrences:
        return [(o.segment_id, finding.entity) for o in finding.occurrences]
    return [_slot(finding)]


# Chữ OCR lặp lại ở nhiều đoạn (băng rôn, logo kênh) chỉ thành một nghi vấn.
REPEAT_KINDS = {SourceKind.OCR}
SAME_QUOTE_RATIO = 0.8  # OCR đọc lệch vài ký tự giữa các khung vẫn coi là cùng một dòng chữ
_SEVERITY = list(Severity)
_CONFIDENCE = list(Confidence)


def _fold(text: str) -> str:
    """Bỏ dấu, chữ hoa và dấu câu: OCR hay đọc sai dấu (Í→Ĩ, Ô→Ổ) mà chữ cái vẫn đúng."""
    return " ".join(re.sub(r"[^\w]+", " ", normalize(text)).split())


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def group_repeats(findings: list[Finding], references: list[str] = ()) -> list[Finding]:
    """Gộp các nghi vấn OCR cùng tầng phân tích, đối tượng, danh mục và chữ gần giống nhau
    thành một nghi vấn, ghi các đoạn xuất hiện vào `occurrences`. Giữ thứ tự ban đầu.
    `references` là văn bản đáng tin hơn OCR (tiêu đề, mô tả, lời nói) để sửa trích dẫn."""
    groups: list[tuple[list[str], list[Finding]]] = []
    for finding in findings:
        # Jev đã bỏ OCR trùng trước khi gửi; giữ nguyên văn bản đã gửi làm quote.
        if (
            finding.source_kind not in REPEAT_KINDS
            or finding.start is None
            or finding.analyzer == "jev"
        ):
            continue
        text = _fold(finding.quote)
        for texts, members in groups:
            head = members[0]
            same = (head.analyzer, head.entity, head.category) == (
                finding.analyzer,
                finding.entity,
                finding.category,
            )
            # So với mọi bản đã gộp: các bản đọc lệch nối nhau thành chuỗi vẫn về một nhóm.
            if same and any(_ratio(seen, text) >= SAME_QUOTE_RATIO for seen in texts):
                members.append(finding)
                if text not in texts:
                    texts.append(text)
                break
        else:
            groups.append(([text], [finding]))
    merged = {id(members[0]): _merge(members, references) for _, members in groups}
    grouped = {id(f) for _, members in groups for f in members}
    return [merged.get(id(f), f) for f in findings if id(f) in merged or id(f) not in grouped]


def _reading(quotes: list[str], references: list[str]) -> str:
    """Bản đọc tốt nhất của một dòng chữ OCR lặp lại: bỏ phiếu từng ký tự giữa các bản đọc có
    độ dài phổ biến nhất, rồi nếu tiêu đề, mô tả hay lời nói có đúng câu đó (so sau khi bỏ dấu)
    thì lấy nguyên văn từ đó, vì OCR hay sai dấu."""
    length = Counter(len(q) for q in quotes).most_common(1)[0][0]
    same = [q for q in quotes if len(q) == length]
    voted = "".join(Counter(chars).most_common(1)[0][0] for chars in zip(*same, strict=True))
    target = _fold(voted)
    size = len(target.split())
    best, best_ratio = voted, 0.9  # chỉ thay khi gần như trùng chữ cái
    for text in references:
        words = text.split()
        for n in (size - 1, size, size + 1):
            for i in range(max(0, len(words) - n + 1)):
                candidate = " ".join(words[i : i + n]).strip(",.;:!?\"'“”()")
                ratio = _ratio(_fold(candidate), target)
                if ratio > best_ratio:
                    best, best_ratio = candidate, ratio
    return best


def _merge(members: list[Finding], references: list[str]) -> Finding:
    if len(members) == 1:
        return members[0]
    # Nghi vấn OCR luôn có segment_id và start (quy ước C4).
    members = sorted(members, key=lambda f: f.start or 0.0)
    head = members[0]
    occurrences: dict[str, Occurrence] = {}
    for f in members:
        start, place = f.start or 0.0, str(f.segment_id)
        occurrences.setdefault(
            place, Occurrence(segment_id=place, start=start, end=f.end or start, frame=f.frame)
        )
    triggers = list({t.model_dump_json(): t for f in members for t in f.triggers}.values())
    places = sorted(occurrences.values(), key=lambda o: o.start)
    reason = head.reason
    if len(places) > 1:
        reason += f" Xuất hiện ở {len(places)} đoạn."
    return Finding.model_validate(
        {
            **head.model_dump(),
            "quote": _reading([f.quote for f in members], references),
            "triggers": [t.model_dump() for t in triggers],
            "severity": max((f.severity for f in members), key=_SEVERITY.index),
            "confidence": max((f.confidence for f in members), key=_CONFIDENCE.index),
            "reason": reason,
            "occurrences": [o.model_dump() for o in places] if len(places) > 1 else [],
        }
    )
