"""Gộp nghi vấn OCR lặp lại (băng rôn chạy suốt video) thành một nghi vấn có occurrences."""

from h4wk.analysis.runner import analyze, group_repeats, slots
from h4wk.analysis.static import LexiconEntry
from h4wk.collectors.models import Normalized, Video
from h4wk.core.entities import Entity
from h4wk.media.timeline import FrameOcr, Segment, Timeline

BANNER = ["CHÍNH QUYỀN NVH LÀ ĐỒ NGỐC", "CHĨNH DUYỀN NVH LÀ ĐỒ NGỐC", "CHÍNH QUYỀN NVH LÀ ĐỒ NGỐC"]


def _segment(i: int, texts: list[str]) -> Segment:
    ocr = [
        FrameOcr(frame=f"frames/{i:06d}.jpg", t=i * 10 + 1, text=t, bbox=(0, 0, 2, 2))
        for t in texts
    ]
    return Segment(id=f"seg_{i:04d}", start=i * 10, end=i * 10 + 9, ocr=ocr)


def _analyze(tmp_path, segments, title=""):
    timeline = Timeline(
        schema="h4wk.timeline/1", video_id="v", capture="20261118T154530", segments=segments
    )
    data = Normalized(
        schema="h4wk.normalized/1", video=Video(id="v", channel_id="c", title=title, description="")
    )
    entity = Entity(id="e_01", name="Nguyễn Văn Hùng", abbreviations=["NVH"])
    _, findings, _ = analyze(
        data, timeline, [entity], [LexiconEntry("đồ ngốc", "thử", "insult")], "run", tmp_path
    )
    return findings


def test_banner_in_every_segment_becomes_one_finding(tmp_path):
    # Hai khung trong đoạn 1 cùng có băng rôn, OCR đọc lệch ở đoạn 2.
    segments = [_segment(1, BANNER[:1] * 2), _segment(2, BANNER[1:2]), _segment(3, BANNER[2:])]
    (finding,) = _analyze(tmp_path, segments)
    assert finding.quote == BANNER[0]  # bản đọc gặp nhiều nhất
    assert [o.segment_id for o in finding.occurrences] == ["seg_0001", "seg_0002", "seg_0003"]
    assert (finding.segment_id, finding.start) == ("seg_0001", 10)
    assert [o.start for o in finding.occurrences] == [10, 20, 30]
    assert finding.occurrences[1].frame == "frames/000002.jpg"
    assert finding.reason.endswith("Xuất hiện ở 3 đoạn.")
    assert slots(finding) == [("seg_0001", "e_01"), ("seg_0002", "e_01"), ("seg_0003", "e_01")]


def test_different_text_or_one_segment_stays_separate(tmp_path):
    segments = [
        _segment(1, [BANNER[0], BANNER[0]]),
        _segment(2, ["NVH đồ ngốc, xem video khác"]),
    ]
    findings = _analyze(tmp_path, segments)
    assert [f.segment_id for f in findings] == ["seg_0001", "seg_0002"]
    # Cùng một đoạn: một chỗ xuất hiện thì không cần occurrences.
    assert all(f.occurrences == [] for f in findings)


def test_other_kinds_are_not_grouped(tmp_path):
    segments = [_segment(1, BANNER[:1]), _segment(2, BANNER[:1])]
    (ocr,) = _analyze(tmp_path, segments)
    speech = ocr.model_copy(update={"source_kind": "speech", "occurrences": []})
    assert group_repeats([speech, speech]) == [speech, speech]


def test_quote_is_taken_from_title_when_ocr_misreads_diacritics(tmp_path):
    misread = "CHĨNH DUYỀN NVH LÀ ĐỒ NGỐC"
    segments = [_segment(1, [misread]), _segment(2, ["CHĨNH QUYỀN NVH LẢ ĐỒ NGỐC"])]
    (finding,) = [
        f
        for f in _analyze(tmp_path, segments, title="Tin nóng: CHÍNH QUYỀN NVH LÀ ĐỒ NGỐC!")
        if f.source_kind == "ocr"
    ]
    assert finding.quote == "CHÍNH QUYỀN NVH LÀ ĐỒ NGỐC"
    assert len(finding.occurrences) == 2
