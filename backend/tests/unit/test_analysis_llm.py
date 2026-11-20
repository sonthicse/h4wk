"""T23: tầng LLM của analysis, dùng FakeProvider."""

import json
from itertools import chain, repeat
from pathlib import Path

import pytest

from h4wk.ai.base import ProviderReply
from h4wk.ai.config import AI_CONFIG_PATH
from h4wk.ai.fake import FakeProvider as _FakeProvider
from h4wk.ai.gateway import AIGateway
from h4wk.analysis import llm, runner
from h4wk.analysis.models import Category, EntityHit, Finding
from h4wk.analysis.static import LexiconEntry
from h4wk.collectors.models import Normalized
from h4wk.core.entities import Entity
from h4wk.media.timeline import Timeline

SAMPLE = Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001"
CAPTURE = "20261118T160000"
ENTITY = Entity(id="e_01", name="Trần Văn Mẫu", aliases=["Mẫu Ca"], abbreviations=["TVM"])
INSULT = [LexiconEntry("đồ hèn", "insult", Category.INSULT)]


def FakeProvider(replies):  # noqa: N802
    """Sau các lời đáp định sẵn (cho phần đoạn), phần comment nhận danh sách kết luận rỗng."""
    return _FakeProvider(chain(replies, repeat(ProviderReply('{"verdicts":[]}'))))


def _data() -> tuple[Normalized, Timeline]:
    data = Normalized.model_validate_json(
        (SAMPLE / "captures" / CAPTURE / "normalized.json").read_text(encoding="utf-8")
    )
    timeline = Timeline.model_validate_json(
        (SAMPLE / "derived" / CAPTURE / "timeline.json").read_text(encoding="utf-8")
    )
    return data, timeline


def _gateway(provider: FakeProvider, tmp_path: Path) -> AIGateway:
    return AIGateway(
        {"anthropic": provider},
        config_path=AI_CONFIG_PATH.with_suffix(".toml.example"),
        log_dir=tmp_path,
    )


def _verdict(item_id: str, **fields) -> dict:
    return {
        "item_id": item_id,
        "entity": "e_01",
        "source_kind": "speech",
        "category": "insult",
        "severity": "medium",
        "confidence": "likely",
        "quote": "q",
        "reason": "Lý do.",
    } | fields


def _reply(*verdicts: dict) -> ProviderReply:
    return ProviderReply(json.dumps({"verdicts": list(verdicts)}))


def _run(tmp_path: Path, provider: FakeProvider, data=None, timeline=None, lexicon=None):
    d, t = _data()
    return runner.analyze(
        data or d,
        timeline or t,
        [ENTITY],
        INSULT if lexicon is None else lexicon,
        "r_x",
        tmp_path / "out",
        gateway=_gateway(provider, tmp_path),
    )


def _hits(data, timeline, tmp_path):
    hits, _, _ = runner.analyze(data, timeline, [ENTITY], [], "r", tmp_path / "h")
    return hits


def test_build_items_context_and_cues_only_segment(tmp_path):
    data, timeline = _data()
    items = llm.build_items(data, timeline, _hits(data, timeline, tmp_path))
    by_segment = {i.segment.id: i for i in items if i.segment}
    # seg_0001 nhắc tên: có context sau (seg_0002), chưa có context trước.
    assert by_segment["seg_0001"].payload["context_before"] is None
    assert by_segment["seg_0001"].payload["context_after"]["speech"].startswith("Mọi người")
    assert by_segment["seg_0001"].triggers and by_segment["seg_0001"].triggers[0].via == "speech"
    # seg_0003 chỉ có ảnh chế, không nhắc tên: vẫn là mục, không có dấu hiệu.
    chế = by_segment["seg_0003"]
    assert chế.triggers == [] and chế.frames
    assert chế.payload["context_before"]["speech"].startswith("Mọi người")
    assert chế.payload["context_after"]["speech"].startswith("Hẹn gặp")
    assert {i.kind for i in items if not i.segment} == {"description", "thumbnail"}


def test_unrelated_video_sends_nothing(tmp_path):
    data, timeline = _data()
    provider = FakeProvider(repeat(_reply()))
    entity = Entity(id="e_02", name="Người Khác")
    hits, findings, error = runner.analyze(
        data, timeline, [entity], [], "r", tmp_path / "o", gateway=_gateway(provider, tmp_path)
    )
    assert hits == [] and error is None
    assert llm.build_items(data, timeline, hits) == []
    assert provider.requests == []
    assert not (tmp_path / "o" / "llm.json").exists()


def test_visual_finding_for_meme_only_segment(tmp_path):
    data, timeline = _data()
    items = llm.build_items(data, timeline, _hits(data, timeline, tmp_path))
    meme = next(i for i in items if i.segment and i.segment.id == "seg_0003")
    frame = meme.frames[0]
    provider = FakeProvider(
        [_reply(_verdict(meme.id, source_kind="visual", frame=frame, reason="Ảnh còng tay."))]
    )
    _, findings, error = _run(tmp_path, provider, data, timeline)
    assert error is None
    found = [f for f in findings if f.analyzer == "llm"]
    assert len(found) == 1
    assert found[0].source_kind == "visual" and found[0].frame == frame
    assert found[0].model.provider == "anthropic"
    assert found[0].segment_id == "seg_0003" and found[0].triggers == []


def test_neutral_only_in_llm_json_and_invalid_verdicts_dropped(tmp_path):
    data, timeline = _data()
    items = llm.build_items(data, timeline, _hits(data, timeline, tmp_path))
    ids = {i.segment.id if i.segment else i.kind: i.id for i in items}
    provider = FakeProvider(
        [
            _reply(
                _verdict(ids["seg_0001"], category="neutral"),
                _verdict(ids["seg_0002"], entity="e_99"),  # đối tượng lạ
                _verdict("i_999"),  # mục lạ
                _verdict(ids["seg_0004"], source_kind="title"),  # loại sai cho mục đoạn
                _verdict(ids["seg_0003"], source_kind="visual", frame="khong/co.jpg"),
            )
        ]
    )
    _, findings, _ = _run(tmp_path, provider, data, timeline, lexicon=[])
    out = tmp_path / "out"
    assert [f.segment_id for f in findings] == ["seg_0003"]  # frame lạ được thay bằng frame đầu
    for raw in json.loads((out / "findings.json").read_text(encoding="utf-8")):
        Finding.model_validate(raw)
    records = json.loads((out / "llm.json").read_text(encoding="utf-8"))
    kept = {r["item_id"]: r["kept"] for r in records}
    assert kept == {
        ids["seg_0001"]: False,
        ids["seg_0002"]: False,  # đối tượng lạ
        "i_999": False,  # mục lạ
        ids["seg_0003"]: True,
        ids["seg_0004"]: False,
    }
    by_item = {r["item_id"]: r for r in records}
    assert "error" in by_item[ids["seg_0004"]] and "error" not in by_item[ids["seg_0003"]]
    assert (
        by_item[ids["seg_0002"]]["error"] == by_item["i_999"]["error"] == ("unknown item or entity")
    )


def test_missing_ai_config_keeps_static_findings(tmp_path):
    data, timeline = _data()
    gateway = AIGateway({}, config_path=tmp_path / "none.toml", log_dir=tmp_path)
    _, findings, error = runner.analyze(
        data, timeline, [ENTITY], INSULT, "r_x", tmp_path / "out", gateway=gateway
    )
    assert error and "ai.toml not found" in error
    assert findings and {f.analyzer for f in findings} == {"static"}


def test_schema_error_keeps_static_findings(tmp_path):
    provider = FakeProvider(repeat(ProviderReply("không phải JSON")))
    _, findings, error = _run(tmp_path, provider)
    assert error
    assert findings and {f.analyzer for f in findings} == {"static"}
    stored = json.loads((tmp_path / "out" / "findings.json").read_text(encoding="utf-8"))
    assert len(stored) == len(findings)
    assert not (tmp_path / "out" / "llm.json").exists()


@pytest.mark.parametrize(("category", "static_kept"), [("insult", False), ("neutral", True)])
def test_llm_replaces_static_finding_of_same_item(tmp_path, category, static_kept):
    data, timeline = _data()
    video = data.video.model_copy(update={"description": data.video.description + " đồ hèn"})
    data = data.model_copy(update={"video": video})
    lexicon = [*INSULT, LexiconEntry("lừa đảo", "accusation", Category.UNSUPPORTED_ACCUSATION)]
    items = llm.build_items(data, timeline, _hits(data, timeline, tmp_path))
    seg4 = next(i for i in items if i.segment and i.segment.id == "seg_0004")
    provider = FakeProvider([_reply(_verdict(seg4.id, source_kind="ocr", category=category))])
    _, findings, _ = _run(tmp_path, provider, data, timeline, lexicon=lexicon)
    on_seg4 = [f for f in findings if f.segment_id == "seg_0004"]
    assert {f.analyzer for f in on_seg4} == ({"static"} if static_kept else {"llm"})
    # Nghi vấn tĩnh ở các mục khác không bị đụng tới.
    assert {f.segment_id for f in findings if f.analyzer == "static"} >= {"seg_0001", "seg_0002"}
    assert any(f.source_kind == "description" for f in findings)


def test_static_finding_of_other_entity_survives(tmp_path):
    data, timeline = _data()
    other = Entity(id="e_02", name="Hắn", aliases=[])
    items = llm.build_items(data, timeline, _hits(data, timeline, tmp_path))
    seg1 = next(i for i in items if i.segment and i.segment.id == "seg_0001")
    provider = FakeProvider([_reply(_verdict(seg1.id, category="insult"))])
    lexicon = [LexiconEntry("lừa đảo", "accusation", Category.UNSUPPORTED_ACCUSATION)]
    _, findings, _ = runner.analyze(
        data,
        timeline,
        [ENTITY, other],
        lexicon,
        "r_x",
        tmp_path / "out",
        gateway=_gateway(provider, tmp_path),
    )
    seg1_findings = {(f.analyzer, f.entity) for f in findings if f.segment_id == "seg_0001"}
    assert seg1_findings == {("llm", "e_01"), ("static", "e_02")}


def test_thumbnail_item_only_for_thumbnail_with_hit(tmp_path):
    data, timeline = _data()
    first = timeline.thumbnails[0]
    plain = first.model_copy(update={"file": "sources/ytdlp/other.jpg", "visual": None, "ocr": []})
    hit_one = first.model_copy(update={"visual": None})
    timeline = timeline.model_copy(update={"thumbnails": [hit_one, plain]})
    hits = _hits(data, timeline, tmp_path)
    hits.append(
        EntityHit(entity="e_01", via="thumbnail", frame=first.file),
    )
    items = llm.build_items(data, timeline, hits)
    thumbs = [i for i in items if i.kind == "thumbnail"]
    assert [t.frames for t in thumbs] == [[first.file]]
    assert thumbs[0].triggers[0].frame == first.file


def test_static_finding_of_other_thumbnail_survives(tmp_path):
    data, timeline = _data()
    first = timeline.thumbnails[0]
    a = first.model_copy(update={"ocr": [first.ocr[0].model_copy(update={"text": "TVM đồ hèn"})]})
    b = a.model_copy(update={"file": "sources/ytdlp/other.jpg"})
    timeline = timeline.model_copy(update={"thumbnails": [a, b]})
    hits, static, _ = runner.analyze(data, timeline, [ENTITY], INSULT, "r", tmp_path / "s")
    assert {f.frame for f in static if f.source_kind == "thumbnail"} == {a.file, b.file}
    items = llm.build_items(data, timeline, hits)
    item_a = next(i for i in items if i.kind == "thumbnail" and i.frames == [a.file])
    provider = FakeProvider([_reply(_verdict(item_a.id, source_kind="thumbnail"))])
    _, findings, _ = _run(tmp_path, provider, data, timeline)
    thumbs = {(f.analyzer, f.frame) for f in findings if f.source_kind == "thumbnail"}
    assert thumbs == {("llm", a.file), ("static", b.file)}


def test_ambiguous_frame_drops_verdict(tmp_path):
    data, timeline = _data()
    segment = timeline.segments[2]
    frames = [v.frame for v in segment.visual]
    extra = segment.visual[0].model_copy(update={"frame": "frames/extra.jpg"})
    segment = segment.model_copy(update={"visual": [*segment.visual, extra]})
    segments = [*timeline.segments[:2], segment, *timeline.segments[3:]]
    timeline = timeline.model_copy(update={"segments": segments})
    items = llm.build_items(data, timeline, _hits(data, timeline, tmp_path))
    meme = next(i for i in items if i.segment and i.segment.id == "seg_0003")
    assert len(meme.frames) == 2 and frames[0] in meme.frames
    provider = FakeProvider([_reply(_verdict(meme.id, source_kind="visual", frame="khong/co.jpg"))])
    _, findings, _ = _run(tmp_path, provider, data, timeline, lexicon=[])
    assert findings == []
    records = json.loads((tmp_path / "out" / "llm.json").read_text(encoding="utf-8"))
    assert [(r["item_id"], r["kept"]) for r in records] == [(meme.id, False)]
    assert "no valid frame" in records[0]["error"]


def test_batches_of_eight(tmp_path):
    data, timeline = _data()
    hits = _hits(data, timeline, tmp_path)
    one = llm.build_items(data, timeline, hits)[0]
    items = [one] * 10
    provider = FakeProvider(repeat(_reply()))
    llm.classify(items, [ENTITY], data, timeline, hits, _gateway(provider, tmp_path), "r")
    assert len(provider.requests) == 2


def test_ref_image_hit_on_thumbnail_makes_thumbnail_item(tmp_path):
    data, timeline = _data()
    first = timeline.thumbnails[0]
    timeline = timeline.model_copy(
        update={"thumbnails": [first.model_copy(update={"visual": None})]}
    )
    hits = [
        EntityHit(entity="e_01", via="ref_image", frame=first.file, bbox=(0, 0, 10, 10), score=0.9)
    ]
    items = llm.build_items(data, timeline, hits)
    thumbs = [i for i in items if i.kind == "thumbnail"]
    assert [t.frames for t in thumbs] == [[first.file]]
    assert [t.via for t in thumbs[0].triggers] == ["ref_image"]
