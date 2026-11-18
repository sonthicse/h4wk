"""Tạo các tệp media phái sinh trong thư mục riêng của một bản thu bất biến."""

import json
import subprocess
from pathlib import Path

from h4wk.media.files import atomic_output


def _streams(path: Path) -> list[dict]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-protocol_whitelist",
            "file",
            "-show_entries",
            "stream=codec_type,codec_name,height,channels,sample_rate,pix_fmt,duration",
            "-of",
            "json",
            str(path.resolve()),
        ],
        check=True,
        capture_output=True,
    )
    return json.loads(result.stdout)["streams"]


def _render(path: Path, inputs: list[str], options: list[str]) -> None:
    with atomic_output(path) as temporary:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-xerror",
                "-y",
                *inputs,
                *options,
                str(temporary),
            ],
            check=True,
        )


def _cached_streams(path: Path) -> list[dict]:
    if path.is_file():
        try:
            # Đọc các gói cuối: ffprobe vẫn có thể đọc header của tệp bị cắt dở.
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-xerror",
                    "-protocol_whitelist",
                    "file",
                    "-sseof",
                    "-2",
                    "-i",
                    str(path.resolve()),
                    "-map",
                    "0",
                    "-c",
                    "copy",
                    "-f",
                    "null",
                    "-",
                ],
                check=True,
                capture_output=True,
            )
            return _streams(path)
        except subprocess.CalledProcessError:
            pass
    return []


def prepare_media(
    video: Path, output_dir: Path, *, audio_source: Path | None = None
) -> tuple[Path, Path]:
    proxy = output_dir / "proxy_480p.mp4"
    wav = output_dir / "audio_16k.wav"
    video_input = ["-protocol_whitelist", "file", "-i", str(video.resolve())]
    audio_input = ["-protocol_whitelist", "file", "-i", str((audio_source or video).resolve())]
    source = _streams(video)
    separate_audio = audio_source is not None
    has_audio = separate_audio or any(s["codec_type"] == "audio" for s in source)
    cached = _cached_streams(proxy)
    valid_video = any(
        s["codec_name"] == "h264" and s.get("height") == 480 and s.get("pix_fmt") == "yuv420p"
        for s in cached
    )
    valid_audio = any(s["codec_name"] == "aac" for s in cached)
    if not valid_video or has_audio != valid_audio:
        inputs = video_input + (audio_input if separate_audio else [])
        options = [
            "-map",
            "0:v:0",
            "-vf",
            "scale=-2:480",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
        ]
        if has_audio:
            options.extend(["-map", "1:a:0" if separate_audio else "0:a:0", "-c:a", "aac"])
        _render(proxy, inputs, options)

    cached = _cached_streams(wav)
    if not any(
        s["codec_name"] == "pcm_s16le"
        and s.get("channels") == 1
        and s.get("sample_rate") == "16000"
        for s in cached
    ):
        if not has_audio:
            # Video câm: giữ đúng độ dài khi tạo track im lặng dành riêng cho STT.
            duration = next(s["duration"] for s in _streams(proxy) if s["codec_type"] == "video")
            audio_input = ["-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", duration]
        _render(
            wav, audio_input, ["-map", "0:a:0", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le"]
        )
    return proxy, wav
