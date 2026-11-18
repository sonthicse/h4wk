"""T8: orchestrator thử nguồn theo thứ tự ưu tiên, chuyển nguồn khi lỗi, ghi manifest."""

import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from h4wk.collectors import registry
from h4wk.collectors.base import (
    Blocked,
    FetchResult,
    NotFound,
    QuotaExceeded,
    Transient,
    Unsupported,
)
from h4wk.collectors.models import Cap, CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator, Settings
from h4wk.collectors.targets import parse_target
from h4wk.core.config_models import SourcesConfig
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import Manifest, Trigger
from h4wk.evidence.verify import FileStatus, verify

VID = "dQw4w9WgXcQ"
ALL = set(Cap)


class FakeCollector:
    """Nguồn giả: outcomes[cap] là danh sách kết quả lần lượt (None = thành công)."""

    def __init__(self, name: str, caps: set[Cap], outcomes: dict | None = None) -> None:
        self.name = name
        self.capabilities = caps
        self.version = "fake-1"
        self.outcomes = {k: list(v) for k, v in (outcomes or {}).items()}
        self.calls: list[Cap] = []

    def fetch(self, cap: Cap, target, workdir: Path) -> FetchResult:  # noqa: ANN001
        self.calls.append(cap)
        queue = self.outcomes.get(cap, [])
        err = queue.pop(0) if queue else None
        if err is not None:
            raise err
        (workdir / f"{cap.value}.json").write_text(f'{{"from": "{self.name}"}}', "utf-8")
        data: dict = {"schema": "h4wk.normalized/1"}
        if cap == Cap.VIDEO_METADATA:
            data["video"] = {"id": target.id, "channel_id": "UCx", "title": f"t-{self.name}"}
        if cap == Cap.COMMENTS:
            data["comments"] = [{"id": "c1", "text": f"c-{self.name}"}]
        if cap == Cap.MEDIA:
            data["media"] = [{"kind": "video", "file": f"sources/{self.name}/v.mp4"}]
            (workdir / "v.mp4").write_bytes(b"mp4")
        return FetchResult(normalized=Normalized.model_validate(data))

    def health_check(self):  # noqa: ANN201
        raise NotImplementedError


class Clock:
    def __init__(self) -> None:
        self.t = datetime(2026, 11, 19, 10, 0, tzinfo=VN_TZ)

    def __call__(self) -> datetime:
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture(autouse=True)
def _unlock_after(data_dir: Path) -> Iterator[None]:
    yield
    for root, dirs, _files in os.walk(data_dir):
        for d in dirs:
            os.chmod(Path(root) / d, 0o755)


def _orch(
    collectors: list[FakeCollector], clock: Clock, case_dir: Path, **settings: object
) -> Orchestrator:
    priority = {c: [x.name for x in collectors] for c in Cap}
    return Orchestrator(
        collectors={c.name: c for c in collectors},
        settings=Settings(priority=priority, **settings),  # type: ignore[arg-type]
        case_dir=case_dir,
        now=clock,
        sleep=lambda _s: None,
    )


def _collect(orch: Orchestrator, level: CollectLevel = CollectLevel.TEXT) -> Manifest:
    cap_dir = orch.collect(
        parse_target(VID), level, collector="user:thi", trigger=Trigger(type="manual")
    )
    return Manifest.model_validate_json((cap_dir / "manifest.json").read_text("utf-8"))


def _norm(m: Manifest, data_dir: Path) -> Normalized:
    d = data_dir / "cases" / "c" / "videos" / VID / "captures"
    latest = sorted(p for p in d.iterdir())[-1]
    return Normalized.model_validate_json((latest / "normalized.json").read_text("utf-8"))


def _calls(m: Manifest, cap: Cap) -> list[tuple[str | None, str]]:
    return [(c.provider, c.status.value) for c in m.sources if c.what == cap]


@pytest.fixture
def case_root(data_dir: Path) -> Path:
    return data_dir / "cases" / "c"


def test_success_uses_first_source(clock: Clock, case_root: Path, data_dir: Path) -> None:
    a, b = FakeCollector("a", ALL), FakeCollector("b", ALL)
    m = _collect(_orch([a, b], clock, case_dir=case_root), CollectLevel.FULL)
    assert b.calls == []
    assert _calls(m, Cap.VIDEO_METADATA) == [("a", "ok")]
    n = _norm(m, data_dir)
    assert n.video and n.video.title == "t-a"
    assert n.provenance[Cap.MEDIA] == "a"
    cap_dir = sorted((case_root / "videos" / VID / "captures").iterdir())[-1]
    assert all(r.status == FileStatus.OK for r in verify(cap_dir))
    assert "sources/a/v.mp4" in m.files


def test_level_decides_caps(clock: Clock, case_root: Path) -> None:
    a = FakeCollector("a", ALL)
    m = _collect(_orch([a], clock, case_dir=case_root), CollectLevel.METADATA)
    assert {c.what for c in m.sources} == {Cap.VIDEO_METADATA, Cap.THUMBNAILS}


def test_blocked_switches_immediately(clock: Clock, case_root: Path, data_dir: Path) -> None:
    a = FakeCollector("a", ALL, {Cap.COMMENTS: [Blocked("bot check")]})
    b = FakeCollector("b", ALL)
    m = _collect(_orch([a, b], clock, case_dir=case_root))
    assert _calls(m, Cap.COMMENTS) == [("a", "blocked"), ("b", "ok")]
    assert _norm(m, data_dir).comments[0].text == "c-b"
    assert next(c for c in m.sources if c.status == "blocked").error == "bot check"


def test_transient_retries_three_times_then_switches(clock: Clock, case_root: Path) -> None:
    a = FakeCollector("a", ALL, {Cap.COMMENTS: [Transient("timeout")] * 4})
    b = FakeCollector("b", ALL)
    m = _collect(_orch([a, b], clock, case_dir=case_root))
    assert _calls(m, Cap.COMMENTS) == [("a", "failed")] * 4 + [("b", "ok")]


def test_transient_then_success(clock: Clock, case_root: Path) -> None:
    a = FakeCollector("a", ALL, {Cap.COMMENTS: [Transient("x"), Transient("x")]})
    m = _collect(_orch([a], clock, case_dir=case_root))
    assert _calls(m, Cap.COMMENTS) == [("a", "failed"), ("a", "failed"), ("a", "ok")]


def test_quota_exceeded_switches(clock: Clock, case_root: Path) -> None:
    a = FakeCollector("a", ALL, {Cap.VIDEO_METADATA: [QuotaExceeded("quota")]})
    b = FakeCollector("b", ALL)
    m = _collect(_orch([a, b], clock, case_dir=case_root))
    assert _calls(m, Cap.VIDEO_METADATA) == [("a", "quota_exceeded"), ("b", "ok")]


def test_unsupported_and_not_found(clock: Clock, case_root: Path) -> None:
    a = FakeCollector(
        "a", ALL, {Cap.VIDEO_METADATA: [Unsupported("no")], Cap.COMMENTS: [NotFound("gone")]}
    )
    b = FakeCollector("b", ALL)
    m = _collect(_orch([a, b], clock, case_dir=case_root))
    assert _calls(m, Cap.VIDEO_METADATA) == [("a", "unsupported"), ("b", "ok")]
    # Video không tồn tại thì không thử nguồn khác.
    assert _calls(m, Cap.COMMENTS) == [("a", "not_found")]


def test_disabled_source_and_no_source(clock: Clock, case_root: Path, data_dir: Path) -> None:
    a = FakeCollector("a", ALL)
    b = FakeCollector("b", ALL - {Cap.MEDIA})
    m = _collect(_orch([a, b], clock, case_dir=case_root, enabled={"a": False}), CollectLevel.FULL)
    assert a.calls == []
    assert _calls(m, Cap.COMMENTS) == [("a", "disabled"), ("b", "ok")]
    assert _calls(m, Cap.MEDIA) == [("a", "disabled"), (None, "no_source")]
    assert _norm(m, data_dir).media == []


def test_all_sources_fail_records_every_call(clock: Clock, case_root: Path) -> None:
    a = FakeCollector("a", ALL, {Cap.COMMENTS: [Blocked("x")]})
    b = FakeCollector("b", ALL, {Cap.COMMENTS: [QuotaExceeded("y")]})
    m = _collect(_orch([a, b], clock, case_dir=case_root))
    assert _calls(m, Cap.COMMENTS) == [
        ("a", "blocked"),
        ("b", "quota_exceeded"),
        (None, "no_source"),
    ]


def test_fault_injection_blocks_without_calling(clock: Clock, case_root: Path) -> None:
    a, b = FakeCollector("a", ALL), FakeCollector("b", ALL)
    m = _collect(_orch([a, b], clock, case_dir=case_root, fault_injection={"a"}))
    assert a.calls == []
    assert _calls(m, Cap.VIDEO_METADATA) == [("a", "blocked"), ("b", "ok")]


def test_source_suspended_after_five_consecutive_failures(clock: Clock, case_root: Path) -> None:
    blocked = [Blocked("x")]
    a = FakeCollector(
        "a",
        ALL,
        {
            Cap.VIDEO_METADATA: blocked * 2,
            Cap.THUMBNAILS: blocked,
            Cap.TRANSCRIPTS: blocked,
            Cap.COMMENTS: blocked,
        },
    )
    b = FakeCollector("b", ALL)
    orch = _orch([a, b], clock, case_dir=case_root)
    _collect(orch)  # a lỗi 4 lần liên tiếp (mức text có 4 loại dữ liệu)
    m2 = _collect(orch)  # lần lỗi thứ 5 ở metadata, sau đó a bị tạm ngưng
    assert _calls(m2, Cap.VIDEO_METADATA) == [("a", "blocked"), ("b", "ok")]
    assert _calls(m2, Cap.COMMENTS) == [("a", "suspended"), ("b", "ok")]
    clock.t += timedelta(minutes=31)
    m3 = _collect(orch)
    assert _calls(m3, Cap.COMMENTS) == [("a", "ok")]


def test_success_resets_failure_count(clock: Clock, case_root: Path) -> None:
    a = FakeCollector("a", ALL, {Cap.VIDEO_METADATA: [Blocked("x")] * 4})
    b = FakeCollector("b", ALL)
    orch = _orch([a, b], clock, case_dir=case_root)
    for _ in range(4):
        _collect(orch)  # mỗi lần: metadata lỗi, comments thành công
    m = _collect(orch)
    assert _calls(m, Cap.VIDEO_METADATA)[0] == ("a", "ok")


def test_new_adapter_needs_one_file_and_one_registry_line(
    clock: Clock, case_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "Một file" là lớp FakeCollector ở trên; "một dòng" là mục trong registry.COLLECTORS.
    monkeypatch.setattr(registry, "COLLECTORS", {"fake": lambda: FakeCollector("fake", ALL)})
    orch = Orchestrator.from_config(
        case_dir=case_root, sources=SourcesConfig(), now=clock, sleep=lambda _s: None
    )
    m = _collect(orch)
    assert _calls(m, Cap.VIDEO_METADATA) == [("fake", "ok")]


def test_previous_capture_on_recollect(clock: Clock, case_root: Path) -> None:
    orch = _orch([FakeCollector("a", ALL)], clock, case_dir=case_root)
    first = _collect(orch)
    second = _collect(orch)
    assert first.previous_capture is None and second.previous_capture is not None


def test_manifest_json_has_vietnam_time(clock: Clock, case_root: Path) -> None:
    orch = _orch([FakeCollector("a", ALL)], clock, case_dir=case_root)
    cap_dir = orch.collect(
        parse_target(VID),
        CollectLevel.METADATA,
        collector="user:thi",
        trigger=Trigger(type="manual"),
    )
    raw = json.loads((cap_dir / "manifest.json").read_text("utf-8"))
    assert raw["collected_at"].endswith("+07:00")
