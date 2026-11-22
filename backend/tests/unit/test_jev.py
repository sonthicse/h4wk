import base64
import io
import json
from urllib.error import HTTPError

import cv2
import numpy as np
import pytest
from _analysis_sample import ENTITY, INSULT, _data

from h4wk.analysis import jev, runner
from h4wk.analysis.models import EntityHit
from h4wk.core.config_models import JevSettings
from h4wk.media.timeline import Frame, FrameOcr, Segment


@pytest.mark.parametrize(
    ("target", "probability", "kept"),
    [("e_01", 0.5, True), ("none", 0.9, False), ("e_01", 0.49, False)],
)
def test_classify(monkeypatch, target, probability, kept):
    data, timeline = _data()
    monkeypatch.setattr(jev.secrets, "get", lambda name: "test-key")
    states = []
    second = ENTITY.model_copy(
        update={
            "id": "e_02",
            "name": "Mẫu hai",
            "aliases": ["Tên khác"],
            "abbreviations": ["MH"],
            "description": "Mô tả mẫu",
        }
    )

    def reply(request, timeout):
        assert (
            request.full_url == jev.URL and request.get_header("Authorization") == "Bearer test-key"
        )
        payload = json.loads(request.data)
        states.append(payload["state"])
        questions = payload["questions"]
        assert set(questions) == {"category", "severity", "is_attack", "target", "violation"}
        criteria = questions["target"]["criteria"]
        assert set(criteria) == {"e_01", "e_02", "none"}
        assert criteria["e_02"] == "Mẫu hai, Tên khác, MH, Mô tả mẫu"
        assert set(questions["category"]["criteria"]["insult"]) == {"what", "examples"}
        return io.BytesIO(
            json.dumps(
                {
                    "model": "jev-test",
                    "answers": {
                        "category": {"probabilities": {"insult": 0.8}},
                        "is_attack": {"noul": probability},
                        "target": {"choice": target},
                        "severity": {"score": 1.5},
                    },
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(jev.urllib.request, "urlopen", reply)
    findings, records, error = jev.classify(
        data, timeline, [ENTITY, second], [], "r_x", JevSettings()
    )
    assert error is None
    assert records and all(r["kept"] == kept for r in records)
    assert any(s.get("parent_comment") for s in states)
    assert {s["source_type"] for s in states} == {
        "YouTube comment",
        "speech transcript segment",
        "video title",
        "video description",
        "video thumbnail image; `text` is the text on it (OCR)",
        "video keyframe images; `text` is the text overlaid on them (OCR)",
    }
    for state in states:
        assert "Mẫu hai, Tên khác, MH, Mô tả mẫu" in state["protected_targets"]
        assert state["text"]
        assert "video_title" in state
        if state["source_type"] == "speech transcript segment":
            assert {"speech_before", "speech_after"} <= state.keys()
        else:
            assert "speech_before" not in state and "speech_after" not in state
    if kept:
        assert {f.source_kind for f in findings} == {
            "speech",
            "comment",
            "title",
            "description",
            "thumbnail",
            "ocr",
        }
        assert all(
            f.entity == target and f.category == "insult" and f.severity == "high" for f in findings
        )
    else:
        assert not findings


def _reply_with(answers, seen=None):
    def reply(request, timeout):
        payload = json.loads(request.data)
        if seen is not None:
            seen.append(payload)
        body = {"model": "jev-test", "answers": answers}
        return io.BytesIO(json.dumps(body).encode("utf-8"))

    return reply


@pytest.mark.parametrize(
    ("violation", "attack", "expected"),
    [
        ({"violence": 0.7, "none": 0.3}, 0.1, ("violence", None)),  # vi phạm theo nội dung
        ({"hate": 0.4, "none": 0.6}, 0.1, None),  # dưới ngưỡng
        ({"violence": 0.35, "hate": 0.3, "none": 0.35}, 0.1, ("violence", None)),  # chia đôi
        ({"violence": 0.55, "none": 0.45}, 0.1, None),  # dưới 0,6
        ({"violence": 0.9}, 0.8, ("insult", "e_01")),  # nhắm vào đối tượng thì ưu tiên
    ],
)
def test_content_violation(monkeypatch, violation, attack, expected):
    data, timeline = _data()
    monkeypatch.setattr(jev.secrets, "get", lambda name: "test-key")
    answers = {
        "category": {"probabilities": {"insult": 0.9}},
        "is_attack": {"noul": attack},
        "target": {"choice": "e_01" if attack >= 0.5 else "none"},
        "severity": {"score": 2},
        "violation": {"probabilities": violation},
    }
    monkeypatch.setattr(jev.urllib.request, "urlopen", _reply_with(answers))
    findings, _, error = jev.classify(data, timeline, [ENTITY], [], "r_x", JevSettings())
    assert error is None
    if expected is None:
        assert findings == []
    else:
        assert findings and {(f.category, f.entity) for f in findings} == {expected}


def test_no_entities_asks_only_content_violations(monkeypatch, tmp_path):
    """Chưa khai báo đối tượng vẫn phát hiện vi phạm theo nội dung."""
    data, timeline = _data()
    monkeypatch.setattr(jev.secrets, "get", lambda name: "test-key")
    seen = []
    answers = {"severity": {"score": 1}, "violation": {"probabilities": {"forgery": 0.95}}}
    monkeypatch.setattr(jev.urllib.request, "urlopen", _reply_with(answers, seen))
    _, findings, error = runner.analyze(
        data, timeline, [], [], "r_x", tmp_path, jev_settings=JevSettings()
    )
    assert error is None and seen
    assert all(set(p["questions"]) == {"violation", "severity"} for p in seen)
    assert all("protected_targets" not in p["state"] for p in seen)
    assert findings and {(f.category, f.entity, f.confidence) for f in findings} == {
        ("forgery", None, "highly_likely")
    }


def test_retry(monkeypatch):
    calls = []
    delays = []

    def reply(request, timeout):
        calls.append(request)
        if len(calls) <= 2:
            raise HTTPError(jev.URL, 429, "", {"retry-after": "0.5"}, None)
        return io.BytesIO(b'{"model":"jev-test"}')

    monkeypatch.setattr(jev.urllib.request, "urlopen", reply)
    monkeypatch.setattr(jev.time, "sleep", delays.append)
    assert jev._call("test-key", {}, {}) == {"model": "jev-test"}
    assert delays == [0.5, 0.5]


@pytest.mark.parametrize("key", [None, "test-key"])
def test_failure_keeps_static(monkeypatch, tmp_path, key):
    monkeypatch.setattr(jev.secrets, "get", lambda name: key)

    def fail(request, timeout):
        assert key
        raise HTTPError(jev.URL, 500, "", {}, None)

    monkeypatch.setattr(jev.urllib.request, "urlopen", fail)
    data, timeline = _data()
    _, findings, error = runner.analyze(
        data, timeline, [ENTITY], INSULT, "r_x", tmp_path, jev_settings=JevSettings()
    )
    assert findings and {f.analyzer for f in findings} == {"static"}
    assert error.startswith("jev:")
    assert ("HTTP 500" if key else "TYPESAFE_API_KEY is not set") in error


def test_new_sources(monkeypatch):
    data, timeline = _data()
    ocr = FrameOcr(text="Dòng chữ mẫu", bbox=[0, 0, 1, 1], frame="frames/a.jpg", t=0)
    frame = Frame(frame="frames/b.jpg", t=2)
    timeline.segments = [
        Segment(id="seg_0001", start=0, end=1, ocr=[ocr, ocr]),
        Segment(
            id="seg_0002", start=1, end=3, ocr=[ocr.model_copy(update={"t": 2})], frames=[frame]
        ),
    ]
    states = []

    def reply(key, state, questions, images=()):
        states.append(state)
        return {
            "model": "jev-test",
            "answers": {
                "category": {"probabilities": {"insult": 0.8}},
                "is_attack": {"noul": 0.5},
                "target": {"choice": ENTITY.id},
                "severity": {"score": 1.0},
            },
        }

    monkeypatch.setattr(jev.secrets, "get", lambda name: "test-key")
    monkeypatch.setattr(jev, "_call", reply)
    hit = EntityHit(entity=ENTITY.id, via="ref_image", segment_id="seg_0002", frame=frame.frame)
    hits = [
        hit,
        hit.model_copy(update={"entity": "e_02"}),
        hit.model_copy(update={"frame": "frames/other.jpg"}),
    ]
    findings, records, error = jev.classify(
        data, timeline, [ENTITY], hits, "r_x", JevSettings(), max_comments=0
    )
    assert error is None
    by_kind = {f.source_kind: f for f in findings}
    assert len(records) == len(findings) == len(by_kind) == 4
    assert set(by_kind) == {"title", "description", "ocr", "thumbnail"}
    assert sum(s["text"].count(ocr.text) for s in states) == 1
    assert by_kind["title"].quote == data.video.title
    assert by_kind["description"].quote == data.video.description
    assert by_kind["thumbnail"].frame == timeline.thumbnails[0].file
    for kind, segment, frame, quote in [
        ("ocr", timeline.segments[0], ocr.frame, ocr.text),
    ]:
        finding = by_kind[kind]
        assert (finding.segment_id, finding.start, finding.end, finding.frame, finding.quote) == (
            segment.id,
            segment.start,
            segment.end,
            frame,
            quote,
        )


def _write(path, width, height):
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), np.full((height, width, 3), 128, np.uint8))
    return path


def _capture_request(monkeypatch):
    sent = []

    def reply(request, timeout):
        sent.append(request)
        return io.BytesIO(b'{"model":"jev-test"}')

    monkeypatch.setattr(jev.urllib.request, "urlopen", reply)
    return sent


def test_call_without_images_has_no_header_and_object_state(monkeypatch):
    sent = _capture_request(monkeypatch)
    jev._call("k", {"text": "a"}, {})
    body = json.loads(sent[0].data)
    assert not any(k.lower() == "typesafe-danger-zone-images" for k in sent[0].headers)
    assert body["state"] == {"text": "a"} and "assets" not in body


def test_call_with_images_resizes_and_lists_state(monkeypatch, tmp_path):
    sent = _capture_request(monkeypatch)
    wide = _write(tmp_path / "wide.jpg", 640, 200)
    tall = _write(tmp_path / "tall.jpg", 270, 480)
    jev._call("k", {"text": "a"}, {}, [wide, tall])
    request = sent[0]
    assert request.get_header("Typesafe-danger-zone-images") == "true"
    body = json.loads(request.data)
    assert body["state"] == ["<image-1>", "<image-2>", {"text": "a"}]
    shapes = []
    for name in ("<image-1>", "<image-2>"):
        asset = body["assets"][name]
        assert asset["type"] == "image" and asset["format"] == "jpeg"
        raw = np.frombuffer(base64.b64decode(asset["data_base64"]), np.uint8)
        shapes.append(cv2.imdecode(raw, cv2.IMREAD_COLOR).shape[:2])
    assert shapes[0] == (320, 1024)  # 640x200 -> 1024x320
    assert min(shapes[1]) == 320


def test_call_unreadable_image_is_value_error(tmp_path):
    with pytest.raises(ValueError, match="Cannot read image"):
        jev._encode(tmp_path / "missing.jpg")


def test_classify_sends_keyframes_and_thumbnail_images(monkeypatch, tmp_path):
    data, timeline = _data()
    derived, capture = tmp_path / "derived", tmp_path / "capture"
    ocr = FrameOcr(text="Dòng chữ", bbox=[0, 0, 1, 1], frame="frames/1.jpg", t=0)
    timeline.segments = [
        Segment(
            id="seg_0001",
            start=0,
            end=10,
            ocr=[ocr, ocr],
            frames=[Frame(frame=f"frames/{i}.jpg", t=i) for i in range(1, 8)],
        ),
        Segment(id="seg_0002", start=10, end=20, frames=[Frame(frame="frames/9.jpg", t=12)]),
    ]
    timeline.thumbnails[0].file = "sources/maxres.jpg"
    calls = []

    def reply(key, state, questions, images=()):
        calls.append((state, list(images)))
        return {
            "model": "jev-test",
            "answers": {
                "category": {"probabilities": {"insult": 0.8}},
                "is_attack": {"noul": 0.9},
                "target": {"choice": ENTITY.id},
                "severity": {"score": 1.0},
            },
        }

    monkeypatch.setattr(jev.secrets, "get", lambda name: "k")
    monkeypatch.setattr(jev, "_call", reply)
    findings, _, error = jev.classify(
        data,
        timeline,
        [ENTITY],
        [],
        "r_x",
        JevSettings(),
        max_comments=0,
        derived_dir=derived,
        capture_dir=capture,
    )
    assert error is None
    by_text = {s["source_type"]: (s, imgs) for s, imgs in calls if imgs}
    keyframes = [(s, imgs) for s, imgs in calls if "keyframe" in s["source_type"]]
    assert len(keyframes) == 2
    # Chọn theo nội dung, không theo thứ tự các luồng.
    first = next(c for c in keyframes if c[0]["text"])
    second = next(c for c in keyframes if not c[0]["text"])
    # 7 keyframe lấy cách đều còn 4; dòng OCR lặp chỉ gửi một lần.
    assert first[0]["text"] == "Dòng chữ"
    assert first[1] == [derived / f"frames/{i}.jpg" for i in (1, 3, 5, 7)]
    assert second[0]["text"] == "" and second[1] == [derived / "frames/9.jpg"]
    # Đoạn chỉ có ảnh sinh nghi vấn visual đúng frame, quote rỗng; đoạn có chữ sinh ocr.
    visual = [f for f in findings if f.source_kind == "visual"]
    assert [(f.segment_id, f.frame, f.quote) for f in visual] == [("seg_0002", "frames/9.jpg", "")]
    ocr_findings = [f for f in findings if f.source_kind == "ocr"]
    assert [(f.segment_id, f.frame, f.quote) for f in ocr_findings] == [
        ("seg_0001", "frames/1.jpg", "Dòng chữ")
    ]
    assert by_text["video thumbnail image; `text` is the text on it (OCR)"][1] == [
        capture / "sources/maxres.jpg"
    ]


def test_classify_without_dirs_sends_text_only(monkeypatch):
    data, timeline = _data()
    timeline.segments = [
        Segment(id="seg_0001", start=0, end=10, frames=[Frame(frame="frames/1.jpg", t=1)])
    ]
    calls = []

    def reply(key, state, questions, images=()):
        calls.append(list(images))
        raise ValueError("stop")

    monkeypatch.setattr(jev.secrets, "get", lambda name: "k")
    monkeypatch.setattr(jev, "_call", reply)
    jev.classify(data, timeline, [ENTITY], [], "r_x", JevSettings(), max_comments=0)
    assert calls and all(images == [] for images in calls)
