"""Nghiệp vụ watchlist (SPEC 10.9): thêm kênh, kiểm tra định kỳ bằng RSS, Check now."""

import time
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlmodel import Session, col, func, select

from h4wk.collectors.models import CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator
from h4wk.collectors.targets import Target, TargetKind, parse_target
from h4wk.core import audit
from h4wk.core.config import CONFIG_DIR, data_dir
from h4wk.core.config_models import SourcesConfig, load_toml
from h4wk.core.db import EventRow, JobRow, KnownVideoRow, WatchItemRow, get_engine
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import Trigger
from h4wk.jobs import pipeline
from h4wk.watchlist import rss

# Kênh theo dõi sẵn làm ví dụ khi khởi tạo (h4wk init): (channel_id, handle, tên).
DEFAULT_CHANNELS = [
    ("UCJDyIKGZ9zpTKDTEXpivGZw", "@VietTan", "Việt Tân"),
    ("UCpoNfKwZbecrcFpzm0ET4uw", "@bbctiengviet", "BBC News Tiếng Việt"),
    ("UCmQoHmnqQBjnCGr0oM4OWKw", "@chantroimoimedia-u4s", "Chân Trời Mới Media"),
    ("UCPK0O9S6qKCVVUc3-IF-BPw", "@luat-khoa", "Luật Khoa tạp chí"),
]

# Có thể thay trong test.
fetch_feed: Callable[[str], list[rss.FeedEntry]] = rss.fetch_feed


def _resolve(target: Target) -> tuple[str, str, str | None]:
    from h4wk.collectors.providers.ytdlp import resolve_channel

    return resolve_channel(target.url)


resolve: Callable[[Target], tuple[str, str, str | None]] = _resolve


class NotFound(LookupError):
    pass


class Duplicate(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(VN_TZ)


def _settings():
    path = CONFIG_DIR / "sources.toml"
    return (load_toml(path, SourcesConfig) if path.exists() else SourcesConfig()).watchlist


def trigger_of(item_id: str) -> str:
    return f"system:watchlist:{item_id}"


def event(kind: str, message: str, **fields: str | None) -> None:
    with Session(get_engine()) as s:
        s.add(EventRow(at=_now(), kind=kind, message=message, **fields))
        s.commit()


def _next_id(s: Session) -> str:
    ids = s.exec(select(WatchItemRow.id)).all()
    n = max((int(i.removeprefix("w_")) for i in ids), default=0) + 1
    return f"w_{n:03d}"


def create_item(channel_id: str, handle: str | None, title: str, level: str) -> WatchItemRow:
    """Thêm mục ở trạng thái chưa khởi tạo; bước thêm kênh chạy ở initialize()."""
    with Session(get_engine()) as s:
        if s.exec(select(WatchItemRow).where(WatchItemRow.channel_id == channel_id)).first():
            raise Duplicate(f"channel {channel_id} is already in the watchlist")
        item = WatchItemRow(
            id=_next_id(s),
            channel_id=channel_id,
            handle=handle,
            title=title,
            level=level,
            created_at=_now(),
        )
        s.add(item)
        s.commit()
        s.refresh(item)
        return item


def add_channel(text: str, level: str) -> WatchItemRow:
    """Thêm kênh từ link kênh, channel ID hoặc @handle."""
    target = parse_target(text)
    if target.kind not in (TargetKind.CHANNEL, TargetKind.HANDLE):
        raise ValueError("not a channel link, channel id or @handle")
    channel_id, title, handle = resolve(target)
    return create_item(channel_id, handle, title, level)


def seed_defaults() -> list[WatchItemRow]:
    """Watchlist trống thì thêm các kênh ví dụ (chưa gọi mạng; khởi tạo ở lần kiểm tra đầu)."""
    with Session(get_engine()) as s:
        if s.exec(select(WatchItemRow.id)).first():
            return []
    # Mức metadata cho nhẹ (40 job full cần GPU và key AI); khi demo đổi kênh cần dùng sang full.
    return [create_item(c, h, title, CollectLevel.METADATA) for c, h, title in DEFAULT_CHANNELS]


def get_item(item_id: str) -> WatchItemRow:
    with Session(get_engine()) as s:
        item = s.get(WatchItemRow, item_id)
    if item is None:
        raise NotFound(item_id)
    return item


def list_items() -> list[WatchItemRow]:
    with Session(get_engine()) as s:
        return list(s.exec(select(WatchItemRow).order_by(WatchItemRow.id)).all())


def update_item(item_id: str, **fields: object) -> WatchItemRow:
    with Session(get_engine()) as s:
        item = s.get(WatchItemRow, item_id)
        if item is None:
            raise NotFound(item_id)
        for k, v in fields.items():
            setattr(item, k, v)
        s.add(item)
        s.commit()
        s.refresh(item)
        return item


def delete_item(item_id: str) -> None:
    with Session(get_engine()) as s:
        item = s.get(WatchItemRow, item_id)
        if item is None:
            raise NotFound(item_id)
        for k in s.exec(select(KnownVideoRow).where(KnownVideoRow.watch_item == item_id)).all():
            s.delete(k)
        s.delete(item)
        s.commit()


def _known(item_id: str) -> set[str]:
    with Session(get_engine()) as s:
        rows = s.exec(select(KnownVideoRow.video_id).where(KnownVideoRow.watch_item == item_id))
        return set(rows.all())


def _mark_known(item_id: str, entries: list[rss.FeedEntry]) -> None:
    known = _known(item_id)
    with Session(get_engine()) as s:
        for e in entries:
            if e.video_id not in known:
                known.add(e.video_id)
                s.add(
                    KnownVideoRow(
                        watch_item=item_id,
                        video_id=e.video_id,
                        title=e.title,
                        published_at=e.published_at,
                        first_seen_at=_now(),
                    )
                )
        s.commit()


def _start_job(item: WatchItemRow, video_id: str) -> str:
    target = parse_target(video_id)
    job = pipeline.create_job(target.url, video_id, item.level, False, trigger_of(item.id))
    pipeline.start(job.id)
    return job.id


def _channel_capture(item: WatchItemRow) -> list[str]:
    """Bản thu hồ sơ kênh trong channels/<channel_id>/captures/; trả về ID video, mới trước."""
    # C1 đặt tên bản thu chính xác đến giây; hai lần thu liền nhau thì chờ sang giây kế.
    now = _now()
    if (data_dir() / "channels" / item.channel_id / "captures" / f"{now:%Y%m%dT%H%M%S}").exists():
        time.sleep(1 - now.microsecond / 1_000_000)
    orch = Orchestrator.from_config(root=data_dir())
    path = orch.collect(
        Target(TargetKind.CHANNEL, item.channel_id),
        CollectLevel.METADATA,
        collector=trigger_of(item.id),
        trigger=Trigger(type="watchlist", watch_item=item.id, event="channel_added"),
    )
    n = Normalized.model_validate_json((path / "normalized.json").read_text(encoding="utf-8"))
    if n.channel and n.channel.title and not item.title:
        update_item(item.id, title=n.channel.title)
    return n.video_ids


def initialize(item: WatchItemRow) -> list[str]:
    """Bước thêm kênh: bản thu hồ sơ kênh, job cho N video mới nhất, đánh dấu feed là đã biết."""
    listed = _channel_capture(item)
    feed = fetch_feed(item.channel_id)
    newest = list(dict.fromkeys([*listed, *(e.video_id for e in feed)]))
    initial = newest[: _settings().initial_videos]
    titles = {e.video_id: e for e in feed}
    _mark_known(
        item.id,
        [titles.get(v) or rss.FeedEntry(v, "", None) for v in newest],
    )
    jobs = [_start_job(item, v) for v in initial]
    update_item(item.id, initialized=True, last_checked_at=_now(), last_error=None)
    event(
        "channel_added",
        f"Started watching {item.title or item.channel_id}: {len(jobs)} latest videos queued",
        watch_item=item.id,
    )
    audit.log(trigger_of(item.id), "watchlist.initialize", item.id, {"jobs": len(jobs)})
    return jobs


def check(item_id: str, *, listing: bool = False) -> list[str]:
    """Kiểm tra một mục; trả về ID video mới. listing=True (Check now) thu thêm danh sách
    video của kênh, vì RSS có thể trễ tới 15 phút."""
    item = get_item(item_id)
    try:
        if not item.initialized:
            initialize(item)
            return []
        entries = fetch_feed(item.channel_id)
        if listing:
            listed = _channel_capture(item)
            have = {e.video_id for e in entries}
            entries += [rss.FeedEntry(v, "", None) for v in listed if v not in have]
        known = _known(item.id)
        new = [e for e in entries if e.video_id not in known]
        _mark_known(item.id, new)
        for e in new:
            job_id = _start_job(item, e.video_id)
            name = item.title or item.channel_id
            event(
                "new_video",
                f"New video detected on {name}: {e.title or e.video_id}",
                watch_item=item.id,
                video_id=e.video_id,
                job_id=job_id,
            )
        update_item(item.id, last_checked_at=_now(), last_error=None)
        return [e.video_id for e in new]
    except Exception as e:
        update_item(item.id, last_checked_at=_now(), last_error=str(e))
        audit.log(trigger_of(item.id), "watchlist.check", item.id, {"error": str(e)}, "error")
        raise


def run_due() -> None:
    """Gọi bởi periodic task: kiểm tra các mục đang bật đã tới chu kỳ."""
    interval = timedelta(minutes=_settings().check_interval_min)
    now = _now()
    for item in list_items():
        last = item.last_checked_at
        if last is not None and last.tzinfo is None:
            from h4wk.core.db import as_aware

            last = as_aware(last)
        if item.enabled and (last is None or now - last >= interval):
            try:
                check(item.id)
            except Exception:  # lỗi đã ghi vào mục và audit; mục khác vẫn chạy
                continue


def latest_video(item_id: str) -> KnownVideoRow | None:
    with Session(get_engine()) as s:
        q = (
            select(KnownVideoRow)
            .where(KnownVideoRow.watch_item == item_id)
            .order_by(col(KnownVideoRow.published_at).desc())
        )
        return s.exec(q).first()


def collected_count(item_id: str) -> int:
    with Session(get_engine()) as s:
        q = select(func.count()).where(
            JobRow.trigger == trigger_of(item_id), JobRow.status == "done"
        )
        return s.exec(q).one()
