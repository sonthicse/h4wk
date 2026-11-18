"""Bước xử lý bản thu full, gọi trong worker GPU với một SttWorker dùng lại giữa các job."""

import logging
from pathlib import Path

from pydantic import ValidationError

from h4wk.collectors.models import Normalized, Transcript, TranscriptSegment
from h4wk.core.config_models import AnalysisConfig
from h4wk.core.types import TranscriptKind
from h4wk.media.files import atomic_output
from h4wk.media.proxy import prepare_media
from h4wk.media.timeline import Timeline
from h4wk.media.transcripts import process_capture

logger = logging.getLogger(__name__)


def _load_model(model_name: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, device="cuda")


class SttWorker:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def transcribe(self, wav: Path, path: Path) -> Transcript:
        if path.is_file():
            try:
                cached = Transcript.model_validate_json(path.read_bytes())
                if cached.kind == TranscriptKind.STT and cached.lang == "vi":
                    return cached
            except ValidationError:
                pass
        if self._model is None:
            self._model = _load_model(self.model_name)
            logger.info("Đã nạp model STT %s", self.model_name)
        segments, _ = self._model.transcribe(str(wav), language="vi", vad_filter=True)
        transcript = Transcript(
            kind=TranscriptKind.STT,
            lang="vi",
            segments=[
                TranscriptSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segments
            ],
        )
        with atomic_output(path) as temporary:
            temporary.write_text(transcript.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return transcript


def process_full_capture(
    capture_dir: Path, output_dir: Path, config: AnalysisConfig, worker: SttWorker
) -> Timeline:
    if output_dir.resolve().is_relative_to(capture_dir.resolve()):
        raise ValueError("Tệp phái sinh phải nằm ngoài thư mục bản thu")
    data = Normalized.model_validate_json((capture_dir / "normalized.json").read_bytes())
    video = next((m for m in data.media if m.kind == "video"), None)
    if data.video is None or video is None:
        raise ValueError("Bản thu full thiếu video")
    audio = next((m for m in data.media if m.kind == "audio"), None)
    _, wav = prepare_media(
        capture_dir / video.file,
        output_dir,
        audio_source=capture_dir / audio.file if audio else None,
    )
    worker.transcribe(wav, output_dir / "transcripts" / "stt.vi.json")
    return process_capture(capture_dir, output_dir, config)
