import pytest

from h4wk.analysis.normalize import matches_name


@pytest.mark.parametrize(
    "text",
    [
        "nguyen van hung",
        "NGUYỄN VĂN HÙNG",
        "Nguyễn Văn Hùnh",
        "Nguyễnn Văn Hùng",
        "Nguyễn Văn Hưng",
        "NVH",
    ],
)
def test_name_matches(text):
    assert matches_name(text, ["Nguyễn Văn Hùng"], ["NVH"])


@pytest.mark.parametrize(
    "text",
    [
        "Nguyễn Văn Hà",
        "Nguyễn Văn Hoàng",
        "Nguyễn Vn Hùng",
        "NVHA",
        "ANVH",
        "Nguyễn Văn",
    ],
)
def test_name_does_not_match(text):
    assert not matches_name(text, ["Nguyễn Văn Hùng"], ["NVH"])


def _lex(*phrases: str) -> list:
    from h4wk.analysis.static import LexiconEntry

    return [LexiconEntry(p, "thử", "insult") for p in phrases]


def test_insults_require_whole_words_and_ignore_diacritics():
    from h4wk.analysis.static import find_insult

    assert find_insult("ĐỒ NGỐC!", _lex("đồ ngốc"))
    assert not find_insult("đồ ngốc nghếch", _lex("ngốc nghếch hơn"))
    assert not find_insult("ngốcn", _lex("ngốc"))


def test_scan_all_sources_and_create_findings_only_for_insults(tmp_path):
    import json

    from h4wk.analysis.runner import analyze
    from h4wk.collectors.models import Comment, Normalized, Video
    from h4wk.core.entities import Entity
    from h4wk.media.timeline import FrameOcr, OcrText, Segment, ThumbnailAnalysis, Timeline

    timeline = Timeline(
        schema="h4wk.timeline/1",
        video_id="v",
        capture="20261118T154530",
        segments=[
            Segment(
                id="seg_0001",
                start=0,
                end=5,
                speech="Nguyễn Văn Hùng",
                ocr=[FrameOcr(frame="frames/1.jpg", t=2, text="NVH đồ ngốc", bbox=(0, 0, 2, 2))],
            )
        ],
        thumbnails=[
            ThumbnailAnalysis(file="thumb.jpg", ocr=[OcrText(text="NVH", bbox=(0, 0, 2, 2))])
        ],
    )
    data = Normalized(
        schema="h4wk.normalized/1",
        video=Video(id="v", channel_id="c", title="NVH", description="NVH đồ ngốc"),
        comments=[Comment(id="c1", text="NVH đồ ngốc")],
    )
    entity = Entity(id="e_01", name="Nguyễn Văn Hùng", abbreviations=["NVH"])
    hits, findings, _ = analyze(data, timeline, [entity], _lex("đồ ngốc"), "run", tmp_path)
    assert {h.via for h in hits} == {
        "speech",
        "ocr",
        "title",
        "description",
        "comment",
        "thumbnail",
    }
    assert {f.source_kind for f in findings} == {"ocr", "description", "comment"}
    assert all(f.category == "insult" and f.severity == "medium" for f in findings)
    assert next(f for f in findings if f.source_kind == "comment").comment_id == "c1"
    assert len({f.id for f in findings}) == len(findings)
    assert all(f.id.startswith("f_") and len(f.id) == 28 for f in findings)
    out = {
        n: json.loads((tmp_path / n).read_text(encoding="utf-8"))
        for n in ("hits.json", "findings.json")
    }
    assert len(out["hits.json"]) == len(hits) and len(out["findings.json"]) == len(findings)


def test_aliases_are_matched(tmp_path):
    from h4wk.analysis.runner import analyze
    from h4wk.collectors.models import Normalized, Video
    from h4wk.core.entities import Entity
    from h4wk.media.timeline import Timeline

    data = Normalized(
        schema="h4wk.normalized/1", video=Video(id="v", channel_id="c", title="Mẫu Ca là đồ hèn")
    )
    timeline = Timeline(schema="h4wk.timeline/1", video_id="v", capture="20261118T154530")
    entity = Entity(id="e_01", name="Trần Văn Mẫu", aliases=["Mẫu Ca"])
    hits, findings, _ = analyze(data, timeline, [entity], None, "run", tmp_path)
    assert [h.via for h in hits] == ["title"] and len(findings) == 1


def test_abbreviation_ignores_case():
    assert matches_name("tvm đã nói", ["Trần Văn Mẫu"], ["TVM"])


def test_lexicon_groups_use_c4_categories():
    from h4wk.analysis.models import Category
    from h4wk.analysis.static import load_lexicon

    lexicon = load_lexicon()
    by_phrase = {e.phrase: e.category for e in lexicon}
    assert by_phrase["đồ hèn"] == Category.INSULT
    assert by_phrase["lừa đảo"] == Category.UNSUPPORTED_ACCUSATION
    assert by_phrase["xuyên tạc"] == Category.FABRICATION
    assert by_phrase["kích động"] == Category.INCITEMENT
    assert by_phrase["bí mật nhà nước"] == Category.STATE_SECRET
    assert len({e.phrase for e in lexicon}) == len(lexicon)  # không trùng cụm từ
    phrases = {e.phrase for e in lexicon}
    assert {"lừa đảo", "đồ hèn", "xuyên tạc", "kích động", "bí mật nhà nước"} <= phrases


def test_unknown_category_in_lexicon_is_rejected(tmp_path):
    from h4wk.analysis.static import load_lexicon

    path = tmp_path / "lex.txt"
    path.write_text("[nhóm: spam]\nabc\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_lexicon(path)


def test_sample_capture_t44_gives_findings(tmp_path):
    from pathlib import Path

    from h4wk.analysis.runner import analyze
    from h4wk.collectors.models import Normalized
    from h4wk.core.entities import Entity
    from h4wk.media.timeline import Timeline

    root = Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001"
    cap = root / "captures/20261118T160000"
    data = Normalized.model_validate_json((cap / "normalized.json").read_text(encoding="utf-8"))
    timeline = Timeline.model_validate_json(
        (root / "derived/20261118T160000/timeline.json").read_text(encoding="utf-8")
    )
    entity = Entity(id="e_01", name="Trần Văn Mẫu", aliases=["Mẫu Ca"], abbreviations=["TVM"])
    hits, findings, _ = analyze(data, timeline, [entity], None, "r_x", tmp_path)
    kinds = sorted(f.source_kind for f in findings)
    # lời nói nhắc tên kèm "lừa đảo", chữ trên hình "TRẦN VĂN MẪU LỪA ĐẢO",
    # chữ góc "TVM đồ hèn", comment "Trần Văn Mẫu đúng là lừa đảo"
    assert kinds == ["comment", "ocr", "ocr", "speech"]
    # Đoạn chỉ có ảnh chế khuôn mặt không có chữ nhắc tên: tầng tĩnh không bắt được (cần T41).
    assert "seg_0003" not in {f.segment_id for f in findings}
