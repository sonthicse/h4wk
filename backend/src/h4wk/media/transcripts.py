"""Gom câu phụ đề thành các đoạn timeline."""

from pathlib import Path

from pydantic import ValidationError

from h4wk.collectors.models import Normalized, Transcript, TranscriptSegment
from h4wk.core.config_models import AnalysisConfig
from h4wk.core.types import TranscriptKind
from h4wk.media.files import atomic_output
from h4wk.media.timeline import Segment, Timeline

SEGMENT_MIN_S = 8
SEGMENT_MAX_S = 30


def _starts_sentence(previous: TranscriptSegment, sentence: TranscriptSegment) -> bool:
    """Mẩu phụ đề mở đầu câu mới: mẩu trước kết thúc bằng dấu câu, hoặc mẩu này viết hoa
    chữ đầu. Mẩu bắt đầu bằng chữ thường là phần tiếp của câu trước."""
    text = sentence.text.lstrip(" -\"“'(")
    return previous.text.rstrip().endswith((".", "?", "!", "…")) or not text[:1].islower()


def group_segments(sentences: list[TranscriptSegment]) -> list[Segment]:
    """Gom mẩu phụ đề thành đoạn dài từ SEGMENT_MIN_S giây, chỉ cắt ở ranh giới câu để một
    câu không bị chia sang hai đoạn; câu quá dài thì cắt khi đoạn vượt SEGMENT_MAX_S giây."""
    groups: list[list[TranscriptSegment]] = []
    for sentence in sorted(sentences, key=lambda item: item.start):
        if groups:
            group = groups[-1]
            end = max(s.end for s in group)
            full = max(sentence.end, end) - group[0].start > SEGMENT_MAX_S
            if not full and (
                end - group[0].start < SEGMENT_MIN_S or not _starts_sentence(group[-1], sentence)
            ):
                group.append(sentence)
                continue
        groups.append([sentence])
    return [
        Segment(
            id=f"seg_{i:04d}",
            start=group[0].start,
            end=max(s.end for s in group),
            speech=" ".join(s.text for s in group),
        )
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
    video_id: str,
    capture: str,
    transcripts: list[Transcript],
    config: AnalysisConfig,
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


def read_capture_timeline(capture_dir: Path, output_dir: Path, config: AnalysisConfig) -> Timeline:
    normalized = Normalized.model_validate_json(
        (capture_dir / "normalized.json").read_text(encoding="utf-8")
    )
    if normalized.video is None:
        raise ValueError("capture has no video")
    transcripts = normalized.transcripts
    stt_path = output_dir / "transcripts" / "stt.vi.json"
    if stt_path.is_file():
        transcripts = [Transcript.model_validate_json(stt_path.read_bytes()), *transcripts]
    return build_timeline(normalized.video.id, capture_dir.name, transcripts, config)


def process_capture(capture_dir: Path, output_dir: Path, config: AnalysisConfig) -> Timeline:
    timeline = read_capture_timeline(capture_dir, output_dir, config)
    path = output_dir / "timeline.json"
    if path.is_file():
        try:
            existing = Timeline.model_validate_json(path.read_bytes())
        except ValidationError:
            pass
        else:
            # OCR, keyframe và hash do bước sau bổ sung; chỉ so phần do bước phụ đề tạo.
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
