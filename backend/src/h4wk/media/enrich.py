"""Ghép các kết quả trên ảnh vào timeline theo C3."""

from collections import defaultdict
from pathlib import Path

from h4wk.media.keyframes import Keyframe
from h4wk.media.ocr import OcrLine
from h4wk.media.timeline import FrameOcr, FrameVisual, OcrText, Segment, ThumbnailAnalysis, Timeline
from h4wk.media.transcripts import write_timeline
from h4wk.media.vision import describe_images


def enrich(
    timeline: Timeline,
    capture: Path,
    out: Path,
    frames: list[Keyframe],
    thumbnails: list[str],
    lines: list[OcrLine],
) -> list[str]:
    """Trả về các file ảnh không có mô tả (VLM lỗi)."""
    images = [(f.file, out / f.file) for f in frames] + [(f, capture / f) for f in thumbnails]
    visuals = describe_images(images, out / "vision.json")
    by_image = defaultdict(list)
    for line in lines:
        by_image[line.frame].append(OcrText(text=line.text, bbox=line.bbox))
    timeline.thumbnails = [
        ThumbnailAnalysis(file=file, visual=visuals.get(file), ocr=by_image[file])
        for file in thumbnails
    ]
    speech = timeline.segments
    segments = list(speech)
    i = 0
    silent = None
    for frame in frames:
        while i < len(speech) and speech[i].end < frame.t:
            i += 1
            silent = None
        if i < len(speech) and speech[i].start <= frame.t:
            segment = speech[i]
        else:
            if silent is None or frame.t - silent.start > 20:
                silent = Segment(id="seg_0001", start=frame.t, end=frame.t)
                segments.append(silent)
            silent.end = frame.t
            segment = silent
        position = {"frame": frame.file, "t": frame.t}
        if frame.file in visuals:
            segment.visual.append(FrameVisual(**position, **visuals[frame.file].model_dump()))
        segment.ocr.extend(FrameOcr(**position, **row.model_dump()) for row in by_image[frame.file])
    timeline.segments = sorted(segments, key=lambda s: s.start)
    for idx, segment in enumerate(timeline.segments, 1):
        segment.id = f"seg_{idx:04d}"
    write_timeline(out / "timeline.json", timeline)
    return [file for file, _ in images if file not in visuals]
