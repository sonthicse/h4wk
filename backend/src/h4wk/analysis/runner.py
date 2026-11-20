"""Phân tích tĩnh văn bản theo các đối tượng cần bảo vệ."""

import json
from pathlib import Path

from h4wk.ai.gateway import AIGateway, GatewayError
from h4wk.analysis import comments, llm
from h4wk.analysis.models import EntityHit, Finding, Trigger
from h4wk.analysis.normalize import matches_name
from h4wk.analysis.static import LexiconEntry, find_insult, load_lexicon
from h4wk.collectors.models import Normalized
from h4wk.core.config_models import CommentSettings
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
    gateway: AIGateway | None = None,
    comment_settings: CommentSettings | None = None,
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

    errors: list[str] = []
    records: list[dict] | None = None
    if gateway is not None:
        settings = comment_settings or CommentSettings()
        items = llm.build_items(data, timeline, hits)
        selected = comments.select_comments(data, hits, settings)
        parts = []
        if items:
            parts.append(
                lambda: llm.classify(items, entities, data, timeline, hits, gateway, run_id)
            )
        if selected:
            parts.append(
                lambda: comments.classify_comments(
                    selected, entities, data, hits, gateway, run_id, timeline, settings
                )
            )
        for part in parts:
            try:
                llm_findings, part_records = part()
            except GatewayError as error:
                # Một phần lỗi thì giữ nghi vấn tĩnh của nó; phần kia vẫn chạy.
                errors.append(str(error))
                continue
            records = (records or []) + part_records
            # LLM kết luận vi phạm cho một mục thì bỏ nghi vấn tĩnh của đúng mục đó.
            replaced = {_slot(f) for f in llm_findings}
            findings = [f for f in findings if _slot(f) not in replaced] + llm_findings
    llm_error = "; ".join(errors) or None

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, items in (("hits.json", hits), ("findings.json", findings)):
        content = [item.model_dump(mode="json", by_alias=True) for item in items]
        _write(output_dir / filename, content)
    if records is not None:
        _write(output_dir / "llm.json", records)
    return hits, findings, llm_error


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
