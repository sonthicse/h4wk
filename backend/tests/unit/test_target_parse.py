"""T8: phân loại đầu vào thành video, kênh, @handle, playlist."""

import pytest

from h4wk.collectors.targets import TargetKind, parse_target

VID = "dQw4w9WgXcQ"
CH = "UCabsTV34JwALXKGMqHpvUiA"
PL = "PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"


@pytest.mark.parametrize(
    ("text", "kind", "ident"),
    [
        (VID, TargetKind.VIDEO, VID),
        (f"https://www.youtube.com/watch?v={VID}", TargetKind.VIDEO, VID),
        (f"https://m.youtube.com/watch?v={VID}&t=42s", TargetKind.VIDEO, VID),
        (f"https://youtu.be/{VID}?si=abc", TargetKind.VIDEO, VID),
        (f"https://www.youtube.com/shorts/{VID}", TargetKind.VIDEO, VID),
        (f"https://www.youtube.com/live/{VID}", TargetKind.VIDEO, VID),
        (f"youtube.com/embed/{VID}", TargetKind.VIDEO, VID),
        (f"https://www.youtube.com/watch?v={VID}&list={PL}", TargetKind.VIDEO, VID),
        (CH, TargetKind.CHANNEL, CH),
        (f"https://www.youtube.com/channel/{CH}/videos", TargetKind.CHANNEL, CH),
        ("@VTV24", TargetKind.HANDLE, "@VTV24"),
        (
            "https://www.youtube.com/@vnexpress.official/videos",
            TargetKind.HANDLE,
            "@vnexpress.official",
        ),
        (f"https://www.youtube.com/playlist?list={PL}", TargetKind.PLAYLIST, PL),
        (PL, TargetKind.PLAYLIST, PL),
        (f"  {VID}  ", TargetKind.VIDEO, VID),
    ],
)
def test_parse(text: str, kind: TargetKind, ident: str) -> None:
    t = parse_target(text)
    assert (t.kind, t.id) == (kind, ident)


def test_video_target_has_canonical_url() -> None:
    assert parse_target(f"https://youtu.be/{VID}").url == f"https://www.youtube.com/watch?v={VID}"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch?v=short",
        "abc",
    ],
)
def test_rejects_invalid(text: str) -> None:
    with pytest.raises(ValueError):
        parse_target(text)
