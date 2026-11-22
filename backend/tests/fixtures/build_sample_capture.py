import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from pydantic import TypeAdapter

from h4wk.analysis.models import EntityHit, Finding
from h4wk.collectors.models import Normalized
from h4wk.evidence.models import Manifest
from h4wk.media.timeline import Timeline

HERE = Path(__file__).resolve().parent
VIDEO_ID = "h4wkDemo001"
CAPTURE = "20261118T160000"
RUN_ID = "r_20261118T160500"
ENTITY = "e_01"
CHANNEL_ID = "UCh4wkDemoChannel000000"
YTDLP_VERSION = "2026.10.26"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

VIDEO_DIR = HERE / "captures" / VIDEO_ID
CAPTURE_DIR = VIDEO_DIR / "captures" / CAPTURE
DERIVED_DIR = VIDEO_DIR / "derived" / CAPTURE
RUN_DIR = DERIVED_DIR / "analysis" / RUN_ID
REFS_DIR = HERE / "refs" / ENTITY
SRC = "sources/ytdlp"

CUES = [
    (0.5, 4.5, "Hôm nay mình nói về Trần Văn Mẫu."),
    (5.0, 9.5, "Ai cũng biết hắn là kẻ lừa đảo."),
    (10.5, 19.0, "Mọi người xem dòng chữ trên màn hình."),
    (20.5, 29.0, "Còn đây là bức ảnh mà ai cũng đang chia sẻ."),
    (30.5, 39.0, "Hẹn gặp lại các bạn ở video sau."),
]
BIG_TEXT = "TRẦN VĂN MẪU LỪA ĐẢO"
MEME_TEXT = "TỘI PHẠM"
CORNER_TEXT = "TVM đồ hèn"
FRAMES = {
    "frames/000015.jpg": 15.0,
    "frames/000025.jpg": 25.0,
    "frames/000032.jpg": 32.0,
    "frames/000034.jpg": 34.5,
}
BBOX_BIG = [36, 165, 566, 42]
BBOX_FACE = [192, 52, 256, 256]
BBOX_REF = [400, 80, 200, 200]
BBOX_CORNER = [545, 336, 88, 18]
BBOX_MEME = [218, 316, 202, 38]
FIDS = [f"f_01JD3Z8K5Q6R7S8T9V0W1X2Y3{c}" for c in "ABCDE"]


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def make_media(tmp: Path) -> None:
    skin, eyes, mouth = (
        "lt(hypot(X-128,Y-128),100)",
        ("lt(hypot(X-95,Y-105),12)+lt(hypot(X-161,Y-105),12)"),
        "lt(abs(hypot(X-128,Y-110)-55),5)*gt(Y,135)",
    )
    geq = ":".join(
        f"{ch}='if({eyes},40,if({mouth},{m},if({skin},{s},{bg})))'"
        for ch, m, s, bg in [("r", 150, 230, 136), ("g", 40, 190, 170), ("b", 40, 160, 204)]
    )
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=256x256:d=1",
        "-vf",
        f"format=rgb24,geq={geq}",
        "-frames:v",
        "1",
        str(tmp / "face.png"),
    )
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=256x256:d=1", "-frames:v", "1", str(tmp / "ref.png"))
    for name, text in [("big.txt", BIG_TEXT), ("meme.txt", MEME_TEXT), ("corner.txt", CORNER_TEXT)]:
        (tmp / name).write_text(text, encoding="utf-8")
    cuffs = np.zeros((72, 168, 4), dtype=np.uint8)
    silver = (205, 205, 205, 255)
    for x in (34, 134):
        cv2.circle(cuffs, (x, 36), 28, silver, 7, cv2.LINE_AA)
    for x in (69, 84, 99):
        cv2.ellipse(cuffs, (x, 36), (10, 5), 0, 0, 360, silver, 3, cv2.LINE_AA)
    (tmp / "cuffs.png").write_bytes(cv2.imencode(".png", cuffs)[1].tobytes())
    vf = (
        "[1:v]scale=256:256[face];"
        "[2:v]crop=200:200:28:28,hue=h=40:s=0.6[ref];"
        "[0:v][face]overlay=192:52:enable='between(t,20,30)'[v1];"
        "[v1][ref]overlay=400:80:enable='between(t,30,38)'[v2];"
        "[v2][4:v]overlay=236:242:enable='between(t,20,30)'[v3];"
        f"[v3]drawtext=fontfile={FONT_BOLD}:textfile={tmp / 'big.txt'}:fontsize=40:"
        "fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,10,20)',"
        f"drawtext=fontfile={FONT_BOLD}:textfile={tmp / 'meme.txt'}:fontsize=36:"
        "fontcolor=red:x=(w-text_w)/2:y=315:enable='between(t,20,30)',"
        f"drawtext=fontfile={FONT}:textfile={tmp / 'corner.txt'}:fontsize=14:"
        "fontcolor=white:x=w-text_w-10:y=h-text_h-10:enable='between(t,34,35)'[v]"
    )
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=c=0x303840:s=640x360:r=25:d=40",
        "-loop",
        "1",
        "-i",
        str(tmp / "face.png"),
        "-loop",
        "1",
        "-i",
        str(tmp / "ref.png"),
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=40",
        "-i",
        str(tmp / "cuffs.png"),
        "-filter_complex",
        vf,
        "-map",
        "[v]",
        "-map",
        "3:a",
        "-t",
        "40",
        "-c:v",
        "libx264",
        "-crf",
        "32",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "32k",
        "-af",
        "volume=0.05",
        "-map_metadata",
        "-1",
        "-fflags",
        "+bitexact",
        "-movflags",
        "+faststart",
        str(tmp / "video.mp4"),
    )
    ffmpeg(
        "-ss",
        "25",
        "-i",
        str(tmp / "video.mp4"),
        "-frames:v",
        "1",
        "-q:v",
        "5",
        str(tmp / "maxres.jpg"),
    )
    for rel, t in FRAMES.items():
        ffmpeg(
            "-ss",
            str(t),
            "-i",
            str(tmp / "video.mp4"),
            "-frames:v",
            "1",
            "-q:v",
            "5",
            str(tmp / Path(rel).name),
        )


def vtt() -> str:
    def ts(s: float) -> str:
        return f"00:00:{int(s):02d}.{int(round(s % 1 * 1000)):03d}"

    return "WEBVTT\nKind: captions\nLanguage: vi\n\n" + "\n".join(
        f"{ts(a)} --> {ts(b)}\n{text}\n" for a, b, text in CUES
    )


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump(model: Any) -> Any:
    return model.model_dump(mode="json", by_alias=True, exclude_none=False)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized() -> Normalized:
    return Normalized.model_validate(
        {
            "schema": "h4wk.normalized/1",
            "video": {
                "id": VIDEO_ID,
                "channel_id": CHANNEL_ID,
                "title": "Video thử nghiệm h4wk",
                "description": "Video tổng hợp dùng cho test. Đối tượng giả: Trần Văn Mẫu.",
                "tags": ["thử nghiệm"],
                "duration_s": 40.0,
                "published_at": "2026-11-18T15:30:00+07:00",
                "view_count": 12,
                "like_count": 1,
                "comment_count": 3,
                "availability": "public",
                "is_live": False,
            },
            "channel": {"id": CHANNEL_ID, "handle": "@h4wkdemo", "title": "Kênh thử nghiệm h4wk"},
            "transcripts": [
                {
                    "kind": "auto",
                    "lang": "vi",
                    "segments": [{"start": a, "end": b, "text": t} for a, b, t in CUES],
                }
            ],
            "comments": [
                {
                    "id": "c1",
                    "author_channel_id": "UCcommenter000000000001",
                    "text": "Trần Văn Mẫu đúng là lừa đảo",
                    "like_count": 4,
                    "published_at": "2026-11-18T15:40:00+07:00",
                },
                {
                    "id": "c1.r1",
                    "parent_id": "c1",
                    "author_channel_id": "UCcommenter000000000002",
                    "text": "đồng ý",
                    "published_at": "2026-11-18T15:45:00+07:00",
                },
                {
                    "id": "c2",
                    "author_channel_id": "UCcommenter000000000003",
                    "text": "Video hay, cảm ơn bạn",
                    "published_at": "2026-11-18T15:50:00+07:00",
                },
            ],
            "thumbnails": [
                {"name": "maxres", "file": f"{SRC}/maxres.jpg", "width": 640, "height": 360}
            ],
            "media": [
                {
                    "kind": "video",
                    "file": f"{SRC}/{VIDEO_ID}.mp4",
                    "height": 360,
                    "vcodec": "h264",
                    "acodec": "aac",
                    "duration_s": 40.0,
                }
            ],
            "provenance": {
                cap: "ytdlp"
                for cap in [
                    "video.metadata",
                    "channel.metadata",
                    "video.transcripts",
                    "video.comments",
                    "video.thumbnails",
                    "video.media",
                ]
            },
        }
    )


def manifest(files: dict[str, Path]) -> Manifest:
    caps = [
        "video.metadata",
        "channel.metadata",
        "video.transcripts",
        "video.comments",
        "video.thumbnails",
        "video.media",
    ]
    return Manifest.model_validate(
        {
            "schema": "h4wk.manifest/1",
            "source_url": f"https://www.youtube.com/watch?v={VIDEO_ID}",
            "collected_at": "2026-11-18T16:00:00+07:00",
            "collector": "user:thi",
            "trigger": {"type": "manual"},
            "level": "full",
            "tool_version": "h4wk 0.1.0",
            "sources": [
                {"provider": "ytdlp", "what": c, "status": "ok", "version": YTDLP_VERSION}
                for c in caps
            ],
            "files": {
                rel: {"sha256": sha256(p), "bytes": p.stat().st_size}
                for rel, p in sorted(files.items())
            },
            "previous_capture": None,
        }
    )


def timeline(video_sha: str) -> Timeline:
    return Timeline.model_validate(
        {
            "schema": "h4wk.timeline/1",
            "video_id": VIDEO_ID,
            "capture": CAPTURE,
            "source_video_sha256": video_sha,
            "transcript_kind": "auto",
            "thumbnails": [
                {
                    "file": f"{SRC}/maxres.jpg",
                    "ocr": [{"text": MEME_TEXT, "bbox": BBOX_MEME}],
                }
            ],
            "segments": [
                {
                    "id": "seg_0001",
                    "start": 0.0,
                    "end": 10.0,
                    "speech": f"{CUES[0][2]} {CUES[1][2]}",
                },
                {
                    "id": "seg_0002",
                    "start": 10.0,
                    "end": 20.0,
                    "speech": CUES[2][2],
                    "ocr": [
                        {
                            "frame": "frames/000015.jpg",
                            "t": 15.0,
                            "text": BIG_TEXT,
                            "bbox": BBOX_BIG,
                        }
                    ],
                },
                {
                    "id": "seg_0003",
                    "start": 20.0,
                    "end": 30.0,
                    "speech": CUES[3][2],
                    "ocr": [
                        {
                            "frame": "frames/000025.jpg",
                            "t": 25.0,
                            "text": MEME_TEXT,
                            "bbox": BBOX_MEME,
                        }
                    ],
                    "frames": [{"frame": "frames/000025.jpg", "t": 25.0}],
                },
                {
                    "id": "seg_0004",
                    "start": 30.0,
                    "end": 40.0,
                    "speech": CUES[4][2],
                    "ocr": [
                        {
                            "frame": "frames/000034.jpg",
                            "t": 34.5,
                            "text": CORNER_TEXT,
                            "bbox": BBOX_CORNER,
                        }
                    ],
                    "frames": [{"frame": "frames/000032.jpg", "t": 32.0}],
                },
            ],
        }
    )


def hits() -> list[EntityHit]:
    return TypeAdapter(list[EntityHit]).validate_python(
        [
            {"entity": ENTITY, "via": "speech", "segment_id": "seg_0001"},
            {
                "entity": ENTITY,
                "via": "ocr",
                "segment_id": "seg_0002",
                "frame": "frames/000015.jpg",
                "bbox": BBOX_BIG,
            },
            {
                "entity": ENTITY,
                "via": "face",
                "segment_id": "seg_0003",
                "frame": "frames/000025.jpg",
                "bbox": BBOX_FACE,
                "score": 0.91,
            },
            {
                "entity": ENTITY,
                "via": "ref_image",
                "segment_id": "seg_0004",
                "frame": "frames/000032.jpg",
                "bbox": BBOX_REF,
                "score": 0.88,
            },
            {
                "entity": ENTITY,
                "via": "ocr",
                "segment_id": "seg_0004",
                "frame": "frames/000034.jpg",
                "bbox": BBOX_CORNER,
            },
            {"entity": ENTITY, "via": "description"},
            {"entity": ENTITY, "via": "comment", "comment_id": "c1"},
        ]
    )


def findings() -> list[Finding]:
    base = {
        "run_id": RUN_ID,
        "video_id": VIDEO_ID,
        "capture": CAPTURE,
        "analyzer_version": "0.1.0",
        "entity": ENTITY,
    }
    static = {**base, "analyzer": "static", "confidence": "unverified"}
    jev = {**base, "analyzer": "jev", "model": {"provider": "typesafe", "model": "jev-test"}}
    return TypeAdapter(list[Finding]).validate_python(
        [
            {
                **static,
                "id": FIDS[0],
                "source_kind": "speech",
                "segment_id": "seg_0001",
                "start": 5.0,
                "end": 9.5,
                "quote": CUES[1][2],
                "triggers": [{"via": "speech", "segment_id": "seg_0001"}],
                "category": "insult",
                "severity": "medium",
                "reason": "Từ 'lừa đảo' trong đoạn nhắc tên đối tượng.",
            },
            {
                **static,
                "id": FIDS[1],
                "source_kind": "ocr",
                "segment_id": "seg_0002",
                "start": 10.0,
                "end": 20.0,
                "quote": BIG_TEXT,
                "frame": "frames/000015.jpg",
                "bbox": BBOX_BIG,
                "triggers": [
                    {
                        "via": "ocr",
                        "segment_id": "seg_0002",
                        "frame": "frames/000015.jpg",
                        "bbox": BBOX_BIG,
                    }
                ],
                "category": "insult",
                "severity": "medium",
                "reason": "Chữ trên hình gắn tên đối tượng với từ 'lừa đảo'.",
            },
            {
                **jev,
                "id": FIDS[2],
                "source_kind": "visual",
                "segment_id": "seg_0003",
                "start": 20.0,
                "end": 30.0,
                "quote": "",
                "frame": "frames/000025.jpg",
                "bbox": BBOX_FACE,
                "triggers": [
                    {
                        "via": "face",
                        "segment_id": "seg_0003",
                        "frame": "frames/000025.jpg",
                        "bbox": BBOX_FACE,
                        "score": 0.91,
                    }
                ],
                "category": "insult",
                "severity": "high",
                "confidence": "likely",
                "reason": "Khuôn mặt đối tượng bị đè chữ 'TỘI PHẠM' và vẽ còng tay; "
                "đoạn này không ai nhắc tên.",
            },
            {
                **static,
                "id": FIDS[3],
                "source_kind": "ocr",
                "segment_id": "seg_0004",
                "start": 34.0,
                "end": 35.0,
                "quote": CORNER_TEXT,
                "frame": "frames/000034.jpg",
                "bbox": BBOX_CORNER,
                "triggers": [
                    {
                        "via": "ocr",
                        "segment_id": "seg_0004",
                        "frame": "frames/000034.jpg",
                        "bbox": BBOX_CORNER,
                    }
                ],
                "category": "insult",
                "severity": "low",
                "reason": "Chữ nhỏ ở góc, viết tắt tên đối tượng kèm 'đồ hèn', chỉ hiện 1 giây.",
            },
            {
                **jev,
                "id": FIDS[4],
                "source_kind": "comment",
                "comment_id": "c1",
                "quote": "Trần Văn Mẫu đúng là lừa đảo",
                "triggers": [{"via": "comment", "comment_id": "c1"}],
                "category": "unsupported_accusation",
                "severity": "low",
                "confidence": "likely",
                "reason": "Comment cáo buộc đối tượng lừa đảo mà không đưa bằng chứng.",
            },
        ]
    )


def main() -> None:
    for d in (VIDEO_DIR, REFS_DIR):
        shutil.rmtree(d, ignore_errors=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        make_media(tmp)
        src = CAPTURE_DIR / SRC
        src.mkdir(parents=True)
        shutil.copy(tmp / "video.mp4", src / f"{VIDEO_ID}.mp4")
        shutil.copy(tmp / "maxres.jpg", src / "maxres.jpg")
        (src / f"{VIDEO_ID}.vi-orig.vtt").write_text(vtt(), encoding="utf-8")
        write_json(
            src / f"{VIDEO_ID}.info.json",
            {
                "id": VIDEO_ID,
                "title": "Video thử nghiệm h4wk",
                "channel_id": CHANNEL_ID,
                "duration": 40,
                "note": "info.json rút gọn cho bản thu mẫu tổng hợp",
            },
        )
        for rel in FRAMES:
            (DERIVED_DIR / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(tmp / Path(rel).name, DERIVED_DIR / rel)
        (REFS_DIR / "face").mkdir(parents=True)
        (REFS_DIR / "image").mkdir(parents=True)
        shutil.copy(tmp / "face.png", REFS_DIR / "face" / "face_01.png")
        shutil.copy(tmp / "ref.png", REFS_DIR / "image" / "ref_01.png")

    write_json(CAPTURE_DIR / "normalized.json", dump(normalized()))
    files = {
        p.relative_to(CAPTURE_DIR).as_posix(): p for p in CAPTURE_DIR.rglob("*") if p.is_file()
    }
    m = manifest(files)
    write_json(CAPTURE_DIR / "manifest.json", dump(m))
    video_sha = m.files[f"{SRC}/{VIDEO_ID}.mp4"].sha256
    write_json(DERIVED_DIR / "timeline.json", dump(timeline(video_sha)))
    write_json(RUN_DIR / "hits.json", [dump(h) for h in hits()])
    write_json(RUN_DIR / "findings.json", [dump(f) for f in findings()])
    print(f"đã dựng bản thu mẫu ở {VIDEO_DIR}")


if __name__ == "__main__":
    main()
