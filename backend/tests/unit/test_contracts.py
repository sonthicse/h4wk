"""Test quy ước C1–C5: mỗi mô hình có ví dụ hợp lệ và ví dụ bị từ chối."""

import copy
import json
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from h4wk.analysis.models import EntityHit, Finding, ReviewDecision
from h4wk.collectors.models import Cap, CollectLevel, Normalized
from h4wk.core.config import REPO_ROOT
from h4wk.core.config_models import AnalysisConfig, SourcesConfig, WatchlistConfig, load_toml
from h4wk.core.entities import EntitiesConfig, Entity
from h4wk.evidence.models import Manifest
from h4wk.media.timeline import Timeline

SHA = "a" * 64
FID = "f_01JD3Z8K5Q6R7S8T9V0W1X2Y3Z"  # f_ + ULID

# ---------------------------------------------------------------- ví dụ hợp lệ

MANIFEST: dict[str, Any] = {
    "schema": "h4wk.manifest/1",
    "source_url": "https://www.youtube.com/watch?v=abc123",
    "collected_at": "2026-11-18T15:45:30+07:00",
    "collector": "system:watchlist:w_012",
    "trigger": {"type": "watchlist", "watch_item": "w_012", "event": "new_video"},
    "level": "full",
    "tool_version": "h4wk 0.1.0",
    "sources": [
        {
            "provider": "youtube_api",
            "what": "video.metadata",
            "status": "ok",
            "started_at": "2026-11-18T15:45:30+07:00",
            "duration_ms": 412,
            "cost": {"quota_units": 1},
        },
        {
            "provider": "ytdlp",
            "what": "video.media",
            "status": "blocked",
            "error": "Sign in to confirm you're not a bot",
            "version": "2026.10.26",
        },
        {"provider": "supadata", "what": "video.media", "status": "unsupported"},
        {"provider": None, "what": "video.comments", "status": "no_source"},
    ],
    "files": {
        "normalized.json": {"sha256": SHA, "bytes": 5120},
        "sources/ytdlp/video.mp4": {"sha256": SHA, "bytes": 182334112},
    },
    "previous_capture": None,
}

NORMALIZED: dict[str, Any] = {
    "schema": "h4wk.normalized/1",
    "video": {
        "id": "abc123",
        "channel_id": "UCabsTV34JwALXKGMqHpvUiA",
        "title": "Tiêu đề",
        "description": "Mô tả",
        "tags": ["tin tức"],
        "category": "News & Politics",
        "duration_s": 652.0,
        "published_at": "2026-11-18T15:00:00+07:00",
        "view_count": 10,
        "like_count": 1,
        "comment_count": 2,
        "availability": "public",
        "is_live": False,
    },
    "channel": {
        "id": "UCabsTV34JwALXKGMqHpvUiA",
        "handle": "@VTV24",
        "title": "VTV24",
        "subscriber_count": 1000,
        "links": ["https://vtv.vn"],
    },
    "video_ids": [],
    "transcripts": [
        {
            "kind": "auto",
            "lang": "vi",
            "segments": [{"start": 0.0, "end": 2.5, "text": "xin chào"}],
        }
    ],
    "comments": [
        {
            "id": "c1",
            "parent_id": None,
            "author_channel_id": "UCx",
            "author_name": "@nguoi1",
            "text": "hay",
            "like_count": 3,
        },
        {"id": "c1.r1", "parent_id": "c1", "author_channel_id": "UCy", "text": "đồng ý"},
    ],
    "thumbnails": [{"name": "maxres", "file": "sources/ytdlp/maxres.jpg", "width": 1280}],
    "media": [{"kind": "video", "file": "sources/ytdlp/video.mp4", "height": 720}],
    "provenance": {"video.metadata": "youtube_api", "video.media": "ytdlp"},
}

TIMELINE: dict[str, Any] = {
    "schema": "h4wk.timeline/1",
    "video_id": "abc123",
    "capture": "20261118T154530",
    "source_video_sha256": SHA,
    "transcript_kind": "stt",
    "thumbnails": [
        {
            "file": "thumbnails/maxres.jpg",
            "ocr": [{"text": "TIN NÓNG", "bbox": [10, 10, 200, 40]}],
        }
    ],
    "segments": [
        {
            "id": "seg_0007",
            "start": 92.4,
            "end": 104.1,
            "speech": "…",
            "ocr": [
                {"frame": "frames/000231.jpg", "t": 95.0, "text": "chữ", "bbox": [0, 0, 50, 10]}
            ],
            "frames": [{"frame": "frames/000231.jpg", "t": 95.0}],
        }
    ],
}

HIT: dict[str, Any] = {
    "entity": "e_01",
    "via": "face",
    "segment_id": "seg_0007",
    "comment_id": None,
    "frame": "frames/000231.jpg",
    "bbox": [10, 20, 30, 40],
    "score": 0.82,
}


def _finding(**over: Any) -> dict[str, Any]:
    f: dict[str, Any] = {
        "id": FID,
        "run_id": "r_20261118T160000",
        "video_id": "abc123",
        "capture": "20261118T154530",
        "analyzer": "jev",
        "analyzer_version": "0.1.0",
        "model": {"provider": "typesafe", "model": "jev-1.14.0"},
        "source_kind": "visual",
        "triggers": [
            {"via": "face", "frame": "frames/000231.jpg", "bbox": [10, 20, 30, 40], "score": 0.82}
        ],
        "segment_id": "seg_0007",
        "comment_id": None,
        "start": 92.4,
        "end": 104.1,
        "quote": "…",
        "frame": "frames/000231.jpg",
        "bbox": None,
        "entity": "e_01",
        "category": "insult",
        "severity": "high",
        "confidence": "likely",
        "reason": "Ảnh ghép khuôn mặt đối tượng với còng tay.",
    }
    f.update(over)
    return f


FINDING = _finding()

OCC_1 = {"segment_id": "seg_0007", "start": 92.4, "end": 104.1, "frame": "frames/000231.jpg"}
OCC_2 = {"segment_id": "seg_0009", "start": 120.0, "end": 131.5}

REVIEW: dict[str, Any] = {
    "finding_id": FID,
    "run_id": "r_20261118T160000",
    "status": "confirmed",
    "by": "user:thi",
    "at": "2026-11-18T16:30:00+07:00",
    "note": "",
}

SOURCES: dict[str, Any] = {
    "sources": {
        "ytdlp": {"enabled": True, "cookies_file": None},
        "youtube_api": {"enabled": True},
        "supadata": {"enabled": False, "fault_injection": False},
    },
    "priority": {
        "video.metadata": ["youtube_api", "ytdlp"],
        "video.media": ["ytdlp"],
    },
}

ANALYSIS: dict[str, Any] = {
    "transcript_priority": ["uploaded", "stt", "auto", "supadata_ai"],
    "face": {"enabled": True},
    "ref_image": {"enabled": True, "threshold": 0.85},
    "comments": {"batch_size": 30, "max_per_video": None},
}


# ------------------------------------------------------------ bảng ví dụ hợp lệ


def _set(path: str, value: Any):
    """Trả về hàm sửa một trường theo đường dẫn kiểu 'a.0.b'."""

    def mutate(d: dict[str, Any]) -> dict[str, Any]:
        d = copy.deepcopy(d)
        *parents, last = path.split(".")
        node: Any = d
        for p in parents:
            node = node[int(p)] if isinstance(node, list) else node[p]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value
        return d

    return mutate


ENTITIES: dict[str, Any] = {
    "entities": [
        {"id": "e_01", "name": "Nguyễn Văn A", "aliases": ["Ông A"], "abbreviations": ["NVA"]},
        {"id": "e_02", "name": "Công ty B", "description": "Doanh nghiệp"},
    ]
}
WATCHLIST: dict[str, Any] = {
    "channels": [
        {"id": "w_001", "channel_id": "UC1", "handle": "@a", "title": "Kênh A", "level": "full"},
        {"id": "w_002", "channel_id": "UC2", "level": "metadata", "enabled": False},
    ]
}


VALID: list[tuple[Any, dict[str, Any]]] = [
    (Manifest, MANIFEST),
    (Normalized, NORMALIZED),
    (Timeline, TIMELINE),
    (EntityHit, HIT),
    (Finding, FINDING),
    (Finding, _finding(category="incitement")),
    (Finding, _finding(category="state_secret")),
    (Finding, _finding(category="violence", entity=None)),
    (Finding, _finding(category="hate", entity=None)),
    (Finding, _finding(category="forgery", entity=None)),
    (Finding, _finding(occurrences=[OCC_1, OCC_2])),
    (ReviewDecision, REVIEW),
    (SourcesConfig, SOURCES),
    (AnalysisConfig, ANALYSIS),
    (EntitiesConfig, ENTITIES),
    (EntitiesConfig, {}),
    (WatchlistConfig, WATCHLIST),
    (WatchlistConfig, {}),
]


@pytest.mark.parametrize(("model", "data"), VALID, ids=lambda x: getattr(x, "__name__", ""))
def test_valid_examples(model: type[BaseModel], data: dict[str, Any]) -> None:
    obj = model.model_validate(data)
    # Ghi ra JSON rồi đọc lại phải ra cùng đối tượng.
    assert model.model_validate_json(obj.model_dump_json()) == obj


# ----------------------------------------------------------- ví dụ bị từ chối

REJECTED: list[tuple[type[BaseModel], dict[str, Any], str]] = [
    # C1
    (Manifest, _set("schema", "h4wk.manifest/2")(MANIFEST), "sai phiên bản schema"),
    (Manifest, _set("sources.3.provider", "ytdlp")(MANIFEST), "no_source mà có provider"),
    (Manifest, _set("sources.0.provider", None)(MANIFEST), "ok mà không có provider"),
    (Manifest, _set("sources.0.status", "error")(MANIFEST), "status ngoài 9 giá trị"),
    (Manifest, _set("sources.0.what", "video.everything")(MANIFEST), "what không phải Cap"),
    (Manifest, _set("files", {"../x": {"sha256": SHA, "bytes": 1}})(MANIFEST), "đường dẫn .."),
    (
        Manifest,
        _set("files", {"/etc/x": {"sha256": SHA, "bytes": 1}})(MANIFEST),
        "đường dẫn tuyệt đối",
    ),
    (Manifest, _set("files", {"a.json": {"sha256": "A" * 64, "bytes": 1}})(MANIFEST), "sha256 hoa"),
    (
        Manifest,
        _set("previous_capture", "2026-11-18T15:45:30+07:00")(MANIFEST),
        "sai dạng capture ts",
    ),
    (Manifest, _set("collector", "thi")(MANIFEST), "actor thiếu tiền tố"),
    (
        Manifest,
        _set("collected_at", "2026-11-18T15:45:30")(MANIFEST),
        "thời gian không múi giờ",
    ),
    (Manifest, _set("level", "everything")(MANIFEST), "mức thu không tồn tại"),
    (Manifest, _set("trigger", {"type": "watchlist"})(MANIFEST), "watchlist thiếu watch_item"),
    (Manifest, _set("api_key", "sk-123")(MANIFEST), "trường lạ"),
    # C2
    (Normalized, _set("transcripts.0.kind", "manual")(NORMALIZED), "loại transcript lạ"),
    (
        Normalized,
        _set("transcripts.0.segments.0", {"start": 3.0, "end": 1.0, "text": "x"})(NORMALIZED),
        "end < start",
    ),
    (Normalized, _set("video.view_count", -5)(NORMALIZED), "số đếm âm"),
    (Normalized, _set("provenance", {"video.all": "ytdlp"})(NORMALIZED), "provenance key lạ"),
    (Normalized, _set("media.0.kind", "subtitle")(NORMALIZED), "loại media lạ"),
    (Normalized, _set("comments.0.parent_id", "c1")(NORMALIZED), "comment tự trả lời chính nó"),
    (Normalized, _set("comments.0.author_name", 123)(NORMALIZED), "author_name không phải chuỗi"),
    (Normalized, _set("video.views", 1)(NORMALIZED), "trường lạ"),
    # C3
    (Timeline, _set("segments.0.end", 90.0)(TIMELINE), "end < start"),
    (Timeline, _set("segments.0.ocr.0.t", 200.0)(TIMELINE), "khung hình ngoài đoạn"),
    (Timeline, _set("segments.0.frames.0.t", 200.0)(TIMELINE), "keyframe ngoài đoạn"),
    (Timeline, _set("segments.0.ocr.0.bbox", [0, 0, -1, 10])(TIMELINE), "bbox rộng âm"),
    (Timeline, _set("segments.0.ocr.0.bbox", [0, 0, 1])(TIMELINE), "bbox thiếu số"),
    (Timeline, _set("transcript_kind", "manual")(TIMELINE), "loại transcript lạ"),
    (Timeline, _set("segments.0.id", "7")(TIMELINE), "id đoạn sai dạng"),
    (Timeline, _set("capture", "hôm nay")(TIMELINE), "capture sai dạng"),
    (Timeline, _set("capture", "20261118T084530Z")(TIMELINE), "capture dạng UTC cũ"),
    # C4: hit
    (EntityHit, _set("via", "voice")(HIT), "via lạ"),
    (EntityHit, {**HIT, "via": "comment", "comment_id": None}, "via comment thiếu comment_id"),
    (EntityHit, {**HIT, "via": "face", "frame": None}, "via face thiếu frame"),
    # C4: finding
    (Finding, _finding(source_kind="visual", frame=None), "visual thiếu frame"),
    (
        Finding,
        _finding(source_kind="comment", segment_id=None, comment_id=None),
        "comment thiếu id",
    ),
    (Finding, _finding(model=None), "jev thiếu model"),
    (Finding, _finding(category="insult", entity=None), "xúc phạm thiếu đối tượng"),
    (
        Finding,
        _finding(analyzer="llm", model={"provider": "openrouter", "model": "x"}),
        "nghi vấn của LLM đã bỏ",
    ),
    (Finding, _finding(analyzer="llm", model=None), "nghi vấn llm cũ thiếu model"),
    (Finding, _finding(confidence="87%"), "mức tin cậy dạng phần trăm"),
    (Finding, _finding(category="spam"), "category lạ"),
    (Finding, _finding(case_id="2026-11_case-0007"), "case_id đã bỏ"),
    (Finding, _finding(id="f_0001"), "id không phải ULID"),
    (Finding, _finding(source_kind="speech", segment_id=None), "speech thiếu segment_id"),
    (Finding, _finding(source_kind="ocr", start=None), "ocr thiếu start"),
    (Finding, _finding(source_kind="visual", segment_id=None), "visual thiếu segment_id"),
    (Finding, _finding(id="f_01jd3z8k5q6r7s8t9v0w1x2y3z"), "id ULID chữ thường"),
    (Finding, _finding(key="b" * 64), "trường key đã bỏ"),
    # C4: review
    (ReviewDecision, _set("status", "approved")(REVIEW), "status lạ"),
    (ReviewDecision, _set("by", "thi")(REVIEW), "actor thiếu tiền tố"),
    (ReviewDecision, _set("finding_id", "f_0001")(REVIEW), "finding_id sai dạng"),
    (ReviewDecision, {**REVIEW, "status": "rejected", "note": ""}, "reject không lý do"),
    (ReviewDecision, {**REVIEW, "status": "rejected", "note": "   "}, "reject lý do trắng"),
    # C5: sources
    (SourcesConfig, _set("priority", {"video.media": ["tiktok"]})(SOURCES), "nguồn lạ"),
    (SourcesConfig, _set("priority", {"video.media": ["ytdlp", "ytdlp"]})(SOURCES), "trùng nguồn"),
    (SourcesConfig, _set("sources.youtube_api.api_key", "AIza…")(SOURCES), "secret trong toml"),
    (SourcesConfig, {**SOURCES, "watchlist": {"threads_per_channel": 0}}, "0 luồng mỗi kênh"),
    (SourcesConfig, {**SOURCES, "watchlist": {"threads_per_channel": 9}}, "quá 8 luồng"),
    # C5: analysis
    (AnalysisConfig, _set("transcript_priority", ["uploaded", "uploaded"])(ANALYSIS), "trùng loại"),
    (AnalysisConfig, _set("comments", {"batch_size": 100})(ANALYSIS), "lô ngoài 20–50"),
    (
        AnalysisConfig,
        _set("ref_image", {"enabled": True, "threshold": 1.5})(ANALYSIS),
        "ngưỡng > 1",
    ),
    # C5: entities
    (EntitiesConfig, _set("entities.1.id", "e_01")(ENTITIES), "trùng id đối tượng"),
    (EntitiesConfig, _set("entities.0.id", "nva")(ENTITIES), "id đối tượng sai dạng"),
    (EntitiesConfig, _set("entities.0.name", "")(ENTITIES), "đối tượng thiếu tên"),
    # C5: watchlist
    (WatchlistConfig, _set("channels.1.channel_id", "UC1")(WATCHLIST), "trùng kênh"),
    (WatchlistConfig, _set("channels.1.id", "w_001")(WATCHLIST), "trùng id kênh"),
    (WatchlistConfig, _set("channels.0.level", "video")(WATCHLIST), "mức thu lạ"),
    (WatchlistConfig, _set("channels.0.id", "w_1")(WATCHLIST), "id kênh sai dạng"),
    (
        WatchlistConfig,
        _set("channels.0.initialized", True)(WATCHLIST),
        "trạng thái chạy trong file",
    ),
]


@pytest.mark.parametrize(
    ("model", "data", "why"), REJECTED, ids=[f"{m.__name__}:{w}" for m, _, w in REJECTED]
)
def test_rejected_examples(model: type[BaseModel], data: dict[str, Any], why: str) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(data)


@pytest.mark.parametrize(
    ("why", "message"),
    [
        ("jev thiếu model", "a jev finding needs model"),
        ("xúc phạm thiếu đối tượng", "category insult needs entity"),
        ("nghi vấn của LLM đã bỏ", "removed LLM providers"),
        ("nghi vấn llm cũ thiếu model", "removed LLM providers"),
    ],
)
def test_finding_analyzer_rejected_for_the_right_rule(why: str, message: str) -> None:
    data = next(d for m, d, w in REJECTED if m is Finding and w == why)
    with pytest.raises(ValidationError, match=message):
        Finding.model_validate(data)


@pytest.mark.parametrize(
    ("model", "why", "message"),
    [
        (EntitiesConfig, "trùng id đối tượng", "duplicate entity id"),
        (WatchlistConfig, "trùng kênh", "duplicate channel_id"),
        (WatchlistConfig, "trùng id kênh", "duplicate id"),
        (WatchlistConfig, "trạng thái chạy trong file", "Extra inputs are not permitted"),
    ],
)
def test_config_lists_rejected_for_the_right_rule(model, why: str, message: str) -> None:
    data = next(d for m, d, w in REJECTED if m is model and w == why)
    with pytest.raises(ValidationError, match=message):
        model.model_validate(data)


def test_legacy_jev_finding_becomes_jev() -> None:
    """Nghi vấn cũ của Jev ghi `analyzer: "llm"` với provider `typesafe` được đọc thành `jev`."""
    finding = Finding.model_validate(_finding(analyzer="llm"))
    assert finding.analyzer == "jev"
    assert finding == Finding.model_validate(_finding())


def test_frame_outside_segment_rejected_for_the_right_rule() -> None:
    data = next(d for m, d, why in REJECTED if m is Timeline and why == "keyframe ngoài đoạn")
    assert data["segments"][0]["frames"][0]["t"] == 200.0
    with pytest.raises(ValidationError, match="outside segment seg_0007"):
        Timeline.model_validate(data)


def test_legacy_timeline_visual_becomes_frames() -> None:
    """Timeline cũ: visual của đoạn thành frames, visual của thumbnail bị bỏ."""
    legacy = copy.deepcopy(TIMELINE)
    legacy["segments"][0].pop("frames")
    legacy["segments"][0]["visual"] = [
        {
            "frame": "frames/000231.jpg",
            "t": 95.0,
            "description": "ảnh",
            "offensive_cues": [],
            "provider": "p",
            "model": "m",
        }
    ]
    legacy["thumbnails"][0]["visual"] = {
        "description": "d",
        "offensive_cues": [],
        "provider": "p",
        "model": "m",
    }
    timeline = Timeline.model_validate(legacy)
    assert timeline == Timeline.model_validate(TIMELINE)
    assert "visual" not in timeline.model_dump_json()
    # visual cũ ngoài đoạn vẫn bị chặn như frames.
    legacy["segments"][0]["visual"][0]["t"] = 200.0
    with pytest.raises(ValidationError, match="outside segment"):
        Timeline.model_validate(legacy)


@pytest.mark.parametrize(
    "patch",
    [
        {"segments": None},
        {"segments": 42},
        {"segments": [{"id": "seg_0001", "start": 0, "end": 1, "visual": [{}]}]},
        {"segments": [{"id": "seg_0001", "start": 0, "end": 1, "visual": 5}]},
        {"segments": [{"id": "seg_0001", "start": 0, "end": 1, "visual": ["x"]}]},
        {"thumbnails": 7},
    ],
)
def test_legacy_validator_leaves_wrong_types_to_pydantic(patch: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Timeline.model_validate({**TIMELINE, **patch})


# ------------------------------------------------------------ quy ước chung


def test_datetime_serializes_vietnam_time() -> None:
    m = Manifest.model_validate(MANIFEST)
    dumped = json.loads(m.model_dump_json())
    assert dumped["collected_at"] == "2026-11-18T15:45:30+07:00"
    assert dumped["schema"] == "h4wk.manifest/1"


def test_utc_input_is_converted_to_vietnam_time() -> None:
    # YouTube trả giờ UTC; khi đọc vào phải đổi sang giờ Việt Nam.
    for value in ["2026-11-18T08:45:30Z", datetime(2026, 11, 18, 8, 45, 30, tzinfo=UTC)]:
        m = Manifest.model_validate({**MANIFEST, "collected_at": value})
        assert m.collected_at.utcoffset() == timedelta(hours=7)
        assert json.loads(m.model_dump_json())["collected_at"] == "2026-11-18T15:45:30+07:00"


def test_cap_values_match_manifest_what() -> None:
    assert Cap.VIDEO_METADATA.value == "video.metadata"
    assert Cap.MEDIA.value == "video.media"
    assert {lv.value for lv in CollectLevel} == {"metadata", "text", "full"}


@pytest.mark.parametrize(
    ("occurrences", "message"),
    [
        ([OCC_2, OCC_1], "first occurrence must match"),
        ([OCC_1, {**OCC_2, "start": 50.0}], "sorted by start"),
        ([OCC_1, {**OCC_2, "end": 100.0}], "end must be >= start"),
        ([OCC_1, {**OCC_2, "note": "x"}], "Extra inputs are not permitted"),
    ],
    ids=["chỗ đầu khác start", "chưa sắp theo thời gian", "end < start", "trường lạ"],
)
def test_finding_occurrences_rejected_for_the_right_rule(occurrences, message) -> None:
    with pytest.raises(ValidationError, match=message):
        Finding.model_validate(_finding(occurrences=occurrences))


def test_finding_start_zero_is_valid() -> None:
    Finding.model_validate(_finding(source_kind="speech", start=0.0, end=4.0))


def test_hits_and_findings_files_are_lists() -> None:
    TypeAdapter(list[EntityHit]).validate_python([HIT, HIT])
    TypeAdapter(list[Finding]).validate_python([FINDING])


# ------------------------------------------------------------------- file mẫu


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("sources", SourcesConfig),
        ("analysis", AnalysisConfig),
        ("entities", EntitiesConfig),
        ("watchlist", WatchlistConfig),
    ],
)
def test_config_examples_load(name: str, model: type[BaseModel]) -> None:
    path = REPO_ROOT / "config" / f"{name}.toml.example"
    model.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("concurrency", [0, 17])
def test_jev_concurrency_rejected(concurrency) -> None:
    with pytest.raises(ValidationError) as exc:
        AnalysisConfig.model_validate({"jev": {"concurrency": concurrency}})
    assert exc.value.errors()[0]["loc"] == ("jev", "concurrency")
    assert exc.value.errors()[0]["type"] in {"greater_than_equal", "less_than_equal"}


def test_load_toml_reads_vietnamese_as_utf8(tmp_path: Path) -> None:
    path = tmp_path / "sources.toml"
    path.write_text('[sources.ytdlp]\ncookies_file = "/home/thi/tài liệu/cookies.txt"\n', "utf-8")
    cfg = load_toml(path, SourcesConfig)
    assert cfg.sources.ytdlp.cookies_file == "/home/thi/tài liệu/cookies.txt"


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"finding_ids": []}, "needs finding_ids"),
        ({"categories": []}, "needs categories"),
        ({"severity": None}, "needs severity"),
        ({"violation": "no"}, "must have no categories"),
        ({"categories": ["neutral"]}, "must be violations"),
    ],
)
def test_video_verdict_requires_evidence(fields, message):
    from h4wk.analysis.models import VideoVerdict

    valid = dict(
        run_id="r_x",
        video_id="v",
        capture="20261118T160000",
        at="2026-11-18T16:00:00+07:00",
        violation="yes",
        categories=["incitement"],
        severity="high",
        confidence="likely",
        finding_ids=[f"f_{0:026d}"],
    )
    assert VideoVerdict.model_validate(valid).violation == "yes"
    # Kết luận cũ do LLM viết có trường model: bỏ khi đọc.
    old_model = {"provider": "openrouter", "model": "x"}
    legacy = VideoVerdict.model_validate(valid | {"model": old_model})
    assert legacy == VideoVerdict.model_validate(valid)
    with pytest.raises(ValidationError, match=message):
        VideoVerdict.model_validate(valid | fields)


def test_video_review_decision_contract():
    from h4wk.analysis.models import VideoReviewDecision

    fields = dict(
        video_id="v",
        run_id="r",
        status="rejected",
        by="user:thi",
        at="2026-11-18T16:00:00+07:00",
        note="Không đủ bằng chứng",
    )
    assert VideoReviewDecision.model_validate(fields).status == "rejected"
    with pytest.raises(ValidationError, match="Reject needs a note"):
        VideoReviewDecision.model_validate(fields | {"note": " "})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        VideoReviewDecision.model_validate(fields | {"finding_id": "wrong"})


def test_entity_description():
    entity = {"id": "e_01", "name": "Đối tượng mẫu"}
    assert Entity.model_validate(entity).description is None
    assert Entity.model_validate({**entity, "description": "Mô tả mẫu"}).description == "Mô tả mẫu"
    with pytest.raises(ValidationError) as exc:
        Entity.model_validate({**entity, "description": ["Sai kiểu"]})
    assert [(e["loc"], e["type"]) for e in exc.value.errors()] == [
        (("description",), "string_type")
    ]
