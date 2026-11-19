"""Phân tích tĩnh văn bản theo đối tượng của case."""

import json
from pathlib import Path

from h4wk.analysis.models import EntityHit, Finding, Trigger
from h4wk.analysis.normalize import matches_name
from h4wk.analysis.static import LexiconEntry, find_insult, load_lexicon
from h4wk.collectors.models import Normalized
from h4wk.core.cases import Entity
from h4wk.core.ids import new_ulid
from h4wk.media.timeline import Timeline


def analyze(
    data: Normalized,
    timeline: Timeline,
    entities: list[Entity],
    lexicon: list[LexiconEntry] | None,
    case_id: str,
    run_id: str,
    output_dir: Path,
) -> tuple[list[EntityHit], list[Finding]]:
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
                        case_id=case_id,
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

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, items in (("hits.json", hits), ("findings.json", findings)):
        content = [item.model_dump(mode="json", by_alias=True) for item in items]
        (output_dir / filename).write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return hits, findings
