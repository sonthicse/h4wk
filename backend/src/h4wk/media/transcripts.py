"""Gom câu phụ đề thành các đoạn timeline."""

from pathlib import Path

from pydantic import ValidationError

from h4wk.collectors.models import Normalized, Transcript, TranscriptSegment
from h4wk.core.config_models import AnalysisConfig
from h4wk.core.types import TranscriptKind
from h4wk.media.files import atomic_output
from h4wk.media.timeline import Segment, Timeline


def group_segments(sentences: list[TranscriptSegment]) -> list[Segment]:
    groups: list[list[TranscriptSegment]] = []
    for sentence in sorted(sentences, key=lambda item: item.start):
        if not groups or max(s.end for s in groups[-1]) - groups[-1][0].start >= 8 or (
            max(sentence.end, *(s.end for s in groups[-1])) - groups[-1][0].start > 20
        ):
            groups.append([])
        groups[-1].append(sentence)
    return [
        Segment(id=f"seg_{i:04d}", start=group[0].start,
                end=max(s.end for s in group), speech=" ".join(s.text for s in group))
        for i, group in enumerate(groups, 1)
    ]


def choose_transcript(
    transcripts: list[Transcript], priority: list[TranscriptKind]
) -> Transcript | None:
    for kind in priority:
        for transcript in transcripts:
            if (
                transcript.kind == kind
                and transcript.lang.lower().split("-")[0] == "vi"
                and any(s.text.strip() for s in transcript.segments)
            ):
                return transcript
    return None


def build_timeline(
    video_id: str, capture: str, transcripts: list[Transcript], config: AnalysisConfig,
    source_video_sha256: str | None = None,
) -> Timeline:
    transcript = choose_transcript(transcripts, config.transcript_priority)
    return Timeline(
        schema="h4wk.timeline/1",
        video_id=video_id,
        capture=capture,
        source_video_sha256=source_video_sha256,
        transcript_kind=transcript.kind if transcript else None,
        segments=group_segments(transcript.segments) if transcript else [],
    )


def write_timeline(path: Path, timeline: Timeline) -> None:
    content = timeline.model_dump_json(by_alias=True, indent=2) + "\n"
    if path.exists() and path.read_bytes() == content.encode("utf-8"):
        return
    with atomic_output(path) as temporary:
        temporary.write_text(content, encoding="utf-8")


def process_capture(capture_dir: Path, output_dir: Path, config: AnalysisConfig) -> Timeline:
    normalized = Normalized.model_validate_json(
        (capture_dir / "normalized.json").read_text(encoding="utf-8")
    )
    if normalized.video is None:
        raise ValueError("Bản thu không có video")
    transcripts = normalized.transcripts
    stt_path = output_dir / "transcripts" / "stt.vi.json"
    if stt_path.is_file():
        transcripts = [Transcript.model_validate_json(stt_path.read_bytes()), *transcripts]
    timeline = build_timeline(normalized.video.id, capture_dir.name, transcripts, config)
    path = output_dir / "timeline.json"
    if path.is_file():
        try:
            existing = Timeline.model_validate_json(path.read_bytes())
        except ValidationError:
            pass
        else:
            # OCR, VLM và hash do bước sau bổ sung; chỉ so phần do bước phụ đề tạo.
            speech_fields = {
                "video_id": True,
                "capture": True,
                "transcript_kind": True,
                "segments": {"__all__": {"id", "start", "end", "speech"}},
            }
            previous = existing.model_dump(include=speech_fields)
            if previous == timeline.model_dump(include=speech_fields):
                return existing
    write_timeline(path, timeline)
    return timeline
