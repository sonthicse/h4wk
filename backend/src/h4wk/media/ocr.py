"""OCR các khung do T19 chọn và các thumbnail đã tải trong bản thu."""

import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import Field, ValidationError

from h4wk.collectors.models import Normalized
from h4wk.core.types import Contract, NonNegFloat, RelPath
from h4wk.media import _paddle_ocr
from h4wk.media.files import atomic_output
from h4wk.media.keyframes import FrameIndex
from h4wk.media.timeline import OcrText


class OcrLine(OcrText):
    frame: RelPath
    t: NonNegFloat | None
    score: float = Field(ge=0, le=1)


class _Image(Contract):
    frame: RelPath
    t: NonNegFloat | None
    size: int
    mtime_ns: int


class _OcrOutput(Contract):
    model_revisions: tuple[str, str]
    images: list[_Image]
    lines: list[OcrLine]


def _recognize(paths: list[Path]) -> list[list[dict]]:
    with TemporaryDirectory() as tmp:
        results = Path(tmp) / "lines.jsonl"
        subprocess.run(
            ["uv", "run", "--locked", "--script", _paddle_ocr.__file__, str(results)],
            input=json.dumps([str(p.resolve()) for p in paths]),
            text=True,
            check=True,
            env={**os.environ, "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True"},
        )
        with results.open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream]


def process_ocr(capture_dir: Path, derived_dir: Path) -> list[OcrLine]:
    if derived_dir.resolve().is_relative_to(capture_dir.resolve()):
        raise ValueError("derived files must be outside the capture directory")
    data = Normalized.model_validate_json((capture_dir / "normalized.json").read_bytes())
    sources: list[tuple[Path, str, float | None]] = []
    index_path = derived_dir / "frames/index.json"
    if index_path.exists() or any(item.kind == "video" for item in data.media):
        index = FrameIndex.model_validate_json(index_path.read_bytes())
        sources.extend((derived_dir, f.file, f.t) for f in index.frames)
    sources.extend(
        (capture_dir, file, None)
        for file in dict.fromkeys(thumb.file for thumb in data.thumbnails if thumb.file)
    )

    paths = []
    images = []
    for root, file, t in sources:
        path = (root / file).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(f"image is outside the source directory: {file}")
        stat = path.stat()
        paths.append(path)
        images.append(_Image(frame=file, t=t, size=stat.st_size, mtime_ns=stat.st_mtime_ns))

    revisions = (_paddle_ocr.DET_REV, _paddle_ocr.REC_REV)
    output = derived_dir / "ocr.json"
    if output.is_file():
        try:
            previous = _OcrOutput.model_validate_json(output.read_bytes())
        except ValidationError:
            pass
        else:
            if previous.images == images and previous.model_revisions == revisions:
                return previous.lines

    predictions = _recognize(paths) if paths else []
    lines = [
        OcrLine(frame=image.frame, t=image.t, **row)
        for image, rows in zip(images, predictions, strict=True)
        for row in rows
    ]
    result = _OcrOutput(model_revisions=revisions, images=images, lines=lines)
    with atomic_output(output) as temp:
        temp.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return lines
