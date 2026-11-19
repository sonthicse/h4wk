import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from h4wk.collectors.models import Normalized, Transcript
from h4wk.core.config_models import AnalysisConfig
from h4wk.media import stt
from h4wk.media.proxy import prepare_media
from h4wk.media.stt import SttWorker, process_full_capture


@pytest.fixture
def clip(tmp_path):
    if not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe")):
        pytest.skip("Cần ffmpeg và ffprobe trong PATH")
    source = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=size=960x540:rate=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "1",
            "-ac",
            "2",
            "-c:v",
            "mpeg4",
            str(source),
        ],
        check=True,
    )
    return source


def streams(path):
    return json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)]
        )
    )["streams"]


def test_proxy_audio_and_restart(clip, tmp_path):
    output = tmp_path / "derived"
    proxy, audio = prepare_media(clip, output)
    video, sound = streams(proxy)
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", 854, 480)
    assert video["pix_fmt"] == "yuv420p" and sound["codec_name"] == "aac"
    (wav,) = streams(audio)
    assert (wav["codec_name"], wav["sample_rate"], wav["channels"]) == ("pcm_s16le", "16000", 1)
    original_time = proxy.stat().st_mtime_ns
    audio.write_bytes(b"broken")
    prepare_media(clip, output)
    assert proxy.stat().st_mtime_ns == original_time and streams(audio) == [wav]
    times = [p.stat().st_mtime_ns for p in (proxy, audio)]
    prepare_media(clip, output)
    assert [p.stat().st_mtime_ns for p in (proxy, audio)] == times


def test_separate_audio_track(clip, tmp_path):
    silent = tmp_path / "video.mp4"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(clip), "-an", "-c:v", "copy", str(silent)],
        check=True,
    )
    proxy, wav = prepare_media(silent, tmp_path / "derived", audio_source=clip)
    assert [s["codec_type"] for s in streams(proxy)] == ["video", "audio"]
    assert streams(wav)[0]["sample_rate"] == "16000"


def test_full_capture_runs_stt_even_with_uploaded_captions(clip, tmp_path, monkeypatch, caplog):
    model = Mock()
    model.transcribe.side_effect = lambda *args, **kw: (
        iter([SimpleNamespace(start=0.0, end=0.8, text=" Xin chào ")]),
        None,
    )
    load = Mock(return_value=model)
    monkeypatch.setattr(stt, "_load_model", load)
    worker = SttWorker("test-model")
    caplog.set_level(logging.INFO, logger=stt.__name__)
    for index, expected in enumerate(["stt", "uploaded"]):
        capture = tmp_path / "captures" / f"20261118T10000{index}"
        capture.mkdir(parents=True)
        shutil.copyfile(clip, capture / "original.mp4")
        data = {
            "schema": "h4wk.normalized/1",
            "video": {"id": "vid", "channel_id": "c", "title": "t"},
            "media": [{"kind": "video", "file": "original.mp4"}],
        }
        if index:
            data["transcripts"] = [
                {
                    "kind": "uploaded",
                    "lang": "vi",
                    "segments": [{"start": 0, "end": 1, "text": "Phụ đề gốc"}],
                }
            ]
        original = Normalized.model_validate(data).model_dump_json(by_alias=True)
        (capture / "normalized.json").write_text(original, encoding="utf-8")
        output = tmp_path / "derived" / capture.name
        result = process_full_capture(capture, output, AnalysisConfig(), worker)
        assert result.transcript_kind == expected
        path = output / "transcripts" / "stt.vi.json"
        transcript = Transcript.model_validate_json(path.read_bytes())
        assert transcript.segments[0].model_dump() == {"start": 0, "end": 0.8, "text": "Xin chào"}
        stamp = path.stat().st_mtime_ns
        assert process_full_capture(capture, output, AnalysisConfig(), worker) == result
        assert path.stat().st_mtime_ns == stamp
        assert (capture / "normalized.json").read_text(encoding="utf-8") == original
    assert model.transcribe.call_count == 2
    load.assert_called_once_with("test-model")
    assert sum("test-model" in record.getMessage() for record in caplog.records) == 1


def test_failed_inference_can_resume(tmp_path, monkeypatch):
    def interrupted():
        yield SimpleNamespace(start=0, end=1, text="xin")
        raise RuntimeError("interrupted")

    model = Mock()
    model.transcribe.side_effect = [(interrupted(), None), (iter([]), None)]
    monkeypatch.setattr(stt, "_load_model", lambda name: model)
    worker = SttWorker("demo")
    path = tmp_path / "transcripts" / "stt.vi.json"
    with pytest.raises(RuntimeError, match="interrupted"):
        worker.transcribe(tmp_path / "audio.wav", path)
    assert not path.exists()
    worker.transcribe(tmp_path / "audio.wav", path)
    assert Transcript.model_validate_json(path.read_bytes()).segments == []
    worker.transcribe(tmp_path / "audio.wav", path)
    assert model.transcribe.call_count == 2


@pytest.mark.parametrize("index", [0, 1])
def test_recover_truncated_media_with_valid_header(clip, tmp_path, index):
    output = tmp_path / "derived"
    paths = prepare_media(clip, output)
    path = paths[index]
    size = path.stat().st_size
    with path.open("r+b") as file:
        file.truncate(size // 2)
    prepare_media(clip, output)
    assert path.stat().st_size == size


def test_silent_video_keeps_duration(clip, tmp_path):
    silent = tmp_path / "silent.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(clip), "-an", "-c:v", "copy", str(silent)], check=True
    )
    proxy, wav = prepare_media(silent, tmp_path / "derived")
    (video,) = streams(proxy)
    (audio,) = streams(wav)
    assert float(audio["duration"]) == pytest.approx(float(video["duration"]), abs=0.001)


def test_stt_retry_preserves_ocr(clip, tmp_path, monkeypatch):
    capture = tmp_path / "20261118T130000"
    capture.mkdir()
    shutil.copyfile(clip, capture / "sample.mp4")
    (capture / "normalized.json").write_text(
        json.dumps(
            {
                "schema": "h4wk.normalized/1",
                "video": {"id": "vid", "channel_id": "c", "title": "t"},
                "media": [{"kind": "video", "file": "sample.mp4"}],
            }
        ),
        encoding="utf-8",
    )
    model = Mock()
    model.transcribe.return_value = ([SimpleNamespace(start=0, end=1, text="xin")], None)
    monkeypatch.setattr(stt, "_load_model", lambda name: model)
    worker = SttWorker("test")
    output = tmp_path / "derived"
    process_full_capture(capture, output, AnalysisConfig(), worker)
    path = output / "timeline.json"
    data = json.loads(path.read_bytes())
    data["segments"][0]["ocr"] = [
        {"text": "xin", "bbox": [0, 0, 2, 2], "frame": "frame.jpg", "t": 0.5}
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    stamp = path.stat().st_mtime_ns
    timeline = process_full_capture(capture, output, AnalysisConfig(), worker)
    assert timeline.segments[0].ocr[0].text == "xin"
    assert path.stat().st_mtime_ns == stamp


@pytest.mark.gpu
def test_real_stt_on_sample_capture(tmp_path):
    model = os.getenv("H4WK_STT_MODEL")
    capture = os.getenv("H4WK_T44_CAPTURE")
    if not model or not capture:
        pytest.skip("Cần H4WK_STT_MODEL và H4WK_T44_CAPTURE để chạy nghiệm thu GPU")
    process_full_capture(Path(capture), tmp_path, AnalysisConfig(), SttWorker(model))
    transcript = Transcript.model_validate_json((tmp_path / "transcripts/stt.vi.json").read_bytes())
    assert any(s.text.strip() and 0 <= s.start < s.end for s in transcript.segments)
