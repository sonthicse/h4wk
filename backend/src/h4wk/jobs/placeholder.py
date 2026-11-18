"""Bước media và analyze TẠM THỜI, để luồng tối giản chạy được trước khi có T10 và T11.

- build_timeline: gom các câu của transcript thành đoạn 8–20 giây (T10 sẽ thay).
- analyze: khớp nguyên văn tên, biệt danh, viết tắt và vài từ xúc phạm mẫu (T11 sẽ thay).
"""

import re
import unicodedata

from h4wk.analysis.models import EntityHit, Finding
from h4wk.collectors.models import Normalized
from h4wk.core.cases import CaseFile
from h4wk.core.ids import new_ulid
from h4wk.media.timeline import Segment, Timeline

INSULTS = ["lừa đảo", "đồ hèn"]  # danh sách mẫu; từ điển thật làm ở T11
MIN_SEG, MAX_SEG = 8.0, 20.0


def build_timeline(n: Normalized, video_id: str, capture: str, video_sha: str | None) -> Timeline:
    order = ["uploaded", "stt", "auto", "supadata_ai"]
    ts = sorted(n.transcripts, key=lambda t: order.index(t.kind))
    segments: list[Segment] = []
    if ts:
        buf: list = []
        for cue in ts[0].segments:
            if buf and cue.end - buf[0].start > MAX_SEG:
                segments.append(_segment(len(segments) + 1, buf))
                buf = []
            buf.append(cue)
            if buf[-1].end - buf[0].start >= MIN_SEG:
                segments.append(_segment(len(segments) + 1, buf))
                buf = []
        if buf:
            segments.append(_segment(len(segments) + 1, buf))
    return Timeline.model_validate(
        {
            "schema": "h4wk.timeline/1",
            "video_id": video_id,
            "capture": capture,
            "source_video_sha256": video_sha,
            "transcript_kind": ts[0].kind if ts else None,
            "segments": segments,
        }
    )


def _segment(i: int, cues: list) -> Segment:
    return Segment(
        id=f"seg_{i:04d}",
        start=cues[0].start,
        end=cues[-1].end,
        speech=" ".join(c.text for c in cues),
    )


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def _mentions(text: str, case: CaseFile) -> list[str]:
    found = []
    for e in case.entities:
        names = [e.name, *e.aliases]
        if any(_norm(x) in _norm(text) for x in names) or any(
            re.search(rf"\b{re.escape(a)}\b", text) for a in e.abbreviations
        ):
            found.append(e.id)
    return found


def analyze(
    case: CaseFile, n: Normalized, timeline: Timeline, run_id: str
) -> tuple[list[EntityHit], list[Finding]]:
    hits: list[EntityHit] = []
    findings: list[Finding] = []
    base = {
        "run_id": run_id,
        "case_id": case.id,
        "video_id": timeline.video_id,
        "capture": timeline.capture,
        "analyzer": "static",
        "analyzer_version": "0.0.1",
        "category": "insult",
        "severity": "medium",
        "confidence": "unverified",
    }
    for seg in timeline.segments:
        for ent in _mentions(seg.speech, case):
            hits.append(EntityHit(entity=ent, via="speech", segment_id=seg.id))
            if any(w in _norm(seg.speech) for w in INSULTS):
                findings.append(
                    Finding.model_validate(
                        {
                            **base,
                            "id": f"f_{new_ulid()}",
                            "source_kind": "speech",
                            "segment_id": seg.id,
                            "start": seg.start,
                            "end": seg.end,
                            "quote": seg.speech,
                            "entity": ent,
                            "triggers": [{"via": "speech", "segment_id": seg.id}],
                            "reason": "Đoạn nhắc tên đối tượng có từ xúc phạm (bộ khớp tạm thời).",
                        }
                    )
                )
    for c in n.comments:
        for ent in _mentions(c.text, case):
            hits.append(EntityHit(entity=ent, via="comment", comment_id=c.id))
            if any(w in _norm(c.text) for w in INSULTS):
                findings.append(
                    Finding.model_validate(
                        {
                            **base,
                            "id": f"f_{new_ulid()}",
                            "source_kind": "comment",
                            "comment_id": c.id,
                            "quote": c.text,
                            "entity": ent,
                            "triggers": [{"via": "comment", "comment_id": c.id}],
                            "reason": "Comment nhắc tên đối tượng có từ xúc phạm (bộ khớp tạm).",
                        }
                    )
                )
    return hits, findings
