"""Phân tích tĩnh văn bản theo đối tượng của case."""

import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from h4wk.analysis.models import EntityHit, Finding, Trigger
from h4wk.analysis.normalize import matches_name
from h4wk.analysis.static import contains_insult, load_insults
from h4wk.collectors.models import Normalized
from h4wk.media.timeline import Timeline


@dataclass
class Entity:
    id: str
    names: list[str]
    abbreviations: list[str]


def _finding_id() -> str:
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    chars = []
    for _ in range(26):
        chars.append(alphabet[value & 31])
        value >>= 5
    return "f_" + "".join(reversed(chars))


def analyze(data: Normalized, timeline: Timeline, entities: list[Entity], insults: list[str] | None,
            case_id: str, run_id: str, output_dir: Path) -> tuple[list[EntityHit], list[Finding]]:
    if insults is None:
        insults = load_insults()
    hits: list[EntityHit] = []
    findings: list[Finding] = []

    def scan(text, via, segment=None, comment_id=None, frame=None, bbox=None):
        for entity in entities:
            if not matches_name(text, entity.names, entity.abbreviations):
                continue
            hit = EntityHit(entity=entity.id, via=via, segment_id=segment.id if segment else None,
                            comment_id=comment_id, frame=frame, bbox=bbox)
            hits.append(hit)
            if contains_insult(text, insults):
                findings.append(Finding(
                    id=_finding_id(), run_id=run_id, case_id=case_id, video_id=timeline.video_id,
                    capture=timeline.capture, analyzer="static", analyzer_version="0.1.0",
                    source_kind=via, triggers=[Trigger(**hit.model_dump(exclude={"entity"}))],
                    segment_id=hit.segment_id, comment_id=comment_id,
                    start=segment.start if segment else None, end=segment.end if segment else None,
                    quote=text, frame=frame, bbox=bbox, entity=entity.id, category="insult",
                    severity="medium", confidence="unverified", reason="Có từ ngữ xúc phạm.",
                ))

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
        (output_dir / filename).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    return hits, findings
