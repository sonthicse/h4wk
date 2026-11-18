import pytest

from h4wk.analysis.normalize import matches_name


@pytest.mark.parametrize("text", [
    "nguyen van hung", "NGUYỄN VĂN HÙNG", "Nguyễn Văn Hùnh",
    "Nguyễnn Văn Hùng", "Nguyễn Văn Hưng", "NVH",
])
def test_name_matches(text):
    assert matches_name(text, ["Nguyễn Văn Hùng"], ["NVH"])


@pytest.mark.parametrize("text", [
    "Nguyễn Văn Hà", "Nguyễn Văn Hoàng", "Nguyễn Vn Hùng",
    "NVHA", "ANVH", "Nguyễn Văn",
])
def test_name_does_not_match(text):
    assert not matches_name(text, ["Nguyễn Văn Hùng"], ["NVH"])


def test_insults_require_whole_words_and_ignore_diacritics():
    from h4wk.analysis.static import contains_insult

    assert contains_insult("ĐỒ NGỐC!", ["đồ ngốc"])
    assert not contains_insult("đồ ngốc nghếch", ["ngốc nghếch hơn"])
    assert not contains_insult("ngốcn", ["ngốc"])


def test_scan_all_sources_and_create_findings_only_for_insults(tmp_path):
    import json

    from h4wk.analysis.runner import Entity, analyze
    from h4wk.collectors.models import Comment, Normalized, Video
    from h4wk.media.timeline import FrameOcr, OcrText, Segment, ThumbnailAnalysis, Timeline

    timeline = Timeline(schema="h4wk.timeline/1", video_id="v", capture="20261118T154530",
        segments=[Segment(id="seg_0001", start=0, end=5, speech="Nguyễn Văn Hùng",
            ocr=[FrameOcr(frame="frames/1.jpg", t=2, text="NVH đồ ngốc", bbox=(0, 0, 2, 2))])],
        thumbnails=[ThumbnailAnalysis(file="thumb.jpg", ocr=[
            OcrText(text="NVH", bbox=(0, 0, 2, 2))])])
    data = Normalized(schema="h4wk.normalized/1",
        video=Video(id="v", channel_id="c", title="NVH", description="NVH đồ ngốc"),
        comments=[Comment(id="c1", text="NVH đồ ngốc")])
    hits, findings = analyze(data, timeline, [Entity("e1", ["Nguyễn Văn Hùng"], ["NVH"])],
                             ["đồ ngốc"], "case", "run", tmp_path)
    assert {h.via for h in hits} == {
        "speech", "ocr", "title", "description", "comment", "thumbnail",
    }
    assert {f.source_kind for f in findings} == {"ocr", "description", "comment"}
    assert all(f.category == "insult" and f.severity == "medium" for f in findings)
    assert next(f for f in findings if f.source_kind == "comment").comment_id == "c1"
    assert len({f.id for f in findings}) == len(findings)
    assert len(json.loads((tmp_path / "hits.json").read_text())) == len(hits)
    assert len(json.loads((tmp_path / "findings.json").read_text())) == len(findings)


def test_default_lexicon_detects_insult():
    from h4wk.analysis.static import load_insults

    assert "đồ ngốc" in load_insults()
