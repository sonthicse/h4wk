from h4wk.collectors.models import TranscriptSegment
from h4wk.media.transcripts import group_segments


def test_grouping_respects_maximum_and_keeps_long_sentence():
    sentences = [
        TranscriptSegment(start=a, end=b, text=t)
        for a, b, t in [
            (0, 4, "Một"),
            (4, 9, "Hai"),
            (9, 19, "Ba"),
            (19, 40, "Dài"),
            (40, 42, "Cuối"),
        ]
    ]
    segments = group_segments(sentences)
    assert [(s.start, s.end, s.speech) for s in segments] == [
        (0, 9, "Một Hai"),
        (9, 19, "Ba"),
        (19, 40, "Dài"),
        (40, 42, "Cuối"),
    ]


def test_grouping_cuts_only_between_sentences():
    sentences = [
        TranscriptSegment(start=a, end=b, text=t)
        for a, b, t in [
            (0, 4, "Phía Việt Nam coi Trung Quốc"),
            (4, 9, "là điểm tựa"),  # chữ thường: tiếp câu trước dù đoạn đã đủ 8 giây
            (9, 12, "chiến lược quan trọng nhất"),
            (12, 15, "Đó là lời khẳng định."),
            (15, 20, "Ngày hôm sau"),
            (20, 24, "tờ báo đăng tin"),
            (24, 45, "tiếp nữa"),  # đoạn sẽ dài 33 giây: buộc cắt giữa câu
        ]
    ]
    segments = group_segments(sentences)
    assert [(s.start, s.end) for s in segments] == [(0, 12), (12, 24), (24, 45)]
    assert segments[0].speech.endswith("Trung Quốc là điểm tựa chiến lược quan trọng nhất")


def test_choose_transcript_respects_priority_and_ignores_empty():
    from h4wk.collectors.models import Transcript
    from h4wk.core.types import TranscriptKind
    from h4wk.media.transcripts import choose_transcript

    uploaded = Transcript(kind="uploaded", lang="vi", segments=[])
    auto = Transcript(
        kind="auto",
        lang="vi",
        segments=[
            TranscriptSegment(start=0, end=3, text="xin chào"),
        ],
    )
    assert (
        choose_transcript([uploaded, auto], [TranscriptKind.UPLOADED, TranscriptKind.AUTO]) == auto
    )
    assert choose_transcript([uploaded], [TranscriptKind.UPLOADED]) is None


def test_build_timeline_uses_c3():
    from h4wk.collectors.models import Transcript
    from h4wk.media.transcripts import build_timeline

    transcript = Transcript(
        kind="uploaded",
        lang="vi",
        segments=[
            TranscriptSegment(start=0, end=3, text="xin chào"),
        ],
    )
    result = build_timeline("video", "20261118T154530", [transcript])
    assert result.model_dump(mode="json", by_alias=True)["schema"] == "h4wk.timeline/1"
    assert result.transcript_kind == "uploaded"
    assert result.segments[0].speech == "xin chào"
    assert result.thumbnails == []


def test_write_timeline_is_idempotent(tmp_path):
    from h4wk.media.transcripts import build_timeline, write_timeline

    timeline = build_timeline("video", "20261118T154530", [])
    path = tmp_path / "derived" / "timeline.json"
    write_timeline(path, timeline)
    before = path.stat().st_mtime_ns
    write_timeline(path, timeline)
    assert path.stat().st_mtime_ns == before
    assert '"schema": "h4wk.timeline/1"' in path.read_text(encoding="utf-8")


def test_process_capture_reads_contracts_and_writes_derived(tmp_path):
    import json

    from h4wk.media.transcripts import process_capture

    capture = tmp_path / "captures" / "20261118T154530"
    capture.mkdir(parents=True)
    (capture / "normalized.json").write_text(
        json.dumps(
            {
                "schema": "h4wk.normalized/1",
                "video": {"id": "vid", "channel_id": "chan", "title": "title"},
                "transcripts": [
                    {
                        "kind": "uploaded",
                        "lang": "vi",
                        "segments": [
                            {"start": 0, "end": 3, "text": "Xin chào"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "derived" / capture.name
    result = process_capture(capture, output)
    assert result.segments[0].speech == "Xin chào"
    assert (output / "timeline.json").is_file()
    assert process_capture(capture, output) == result


def test_choose_only_vietnamese_transcripts():
    from h4wk.collectors.models import Transcript
    from h4wk.core.types import TranscriptKind
    from h4wk.media.transcripts import choose_transcript

    segment = TranscriptSegment(start=0, end=1, text="text")
    english = Transcript(kind="uploaded", lang="en", segments=[segment])
    vietnamese = Transcript(kind="auto", lang="vi-VN", segments=[segment])
    assert (
        choose_transcript(
            [english, vietnamese],
            [
                TranscriptKind.UPLOADED,
                TranscriptKind.AUTO,
            ],
        )
        == vietnamese
    )
