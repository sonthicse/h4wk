"""Nghiệp vụ watchlist (SPEC 10.9): thêm kênh, kiểm tra định kỳ bằng RSS, Check now.

Danh sách kênh nằm ở config/watchlist.toml (nguồn gốc, sửa tay được). Database chỉ giữ trạng
thái chạy của từng kênh (đã khởi tạo, lần kiểm tra cuối, lỗi, video đã biết) và được đồng bộ
theo file mỗi lần đọc."""

import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from h4wk.collectors.models import CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator
from h4wk.collectors.targets import Target, TargetKind, parse_target
from h4wk.core import audit, tomlw
from h4wk.core.config import config_dir, data_dir
from h4wk.core.config_models import SourcesConfig, WatchChannel, WatchlistConfig, load_toml
from h4wk.core.db import JobRow, KnownVideoRow, WatchItemRow, get_engine
from h4wk.core.events import record as event
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import Trigger
from h4wk.jobs import pipeline
from h4wk.watchlist import rss

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
    path = config_dir() / "sources.toml"
    return (load_toml(path, SourcesConfig) if path.exists() else SourcesConfig()).watchlist


def trigger_of(item_id: str) -> str:
    return f"system:watchlist:{item_id}"


# ------------------------------------------------------------ config/watchlist.toml

# Trường cấu hình (ghi vào file); trường còn lại của WatchItemRow là trạng thái chạy.
CONFIG_FIELDS = set(WatchChannel.model_fields) - {"id"}


def watchlist_file() -> Path:
    return config_dir() / "watchlist.toml"


def _save_channels(channels: list[WatchChannel]) -> None:
    path = watchlist_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = WatchlistConfig(channels=channels).model_dump(mode="json")
    tmp = path.with_suffix(".toml.tmp")
    tmp.write_text(tomlw.dumps(data), encoding="utf-8")
    tmp.replace(path)


def migrate_legacy() -> bool:
    """Chưa có watchlist.toml mà database còn kênh (cách lưu cũ) thì ghi các kênh đó ra file.
    Trả về True nếu đã ghi."""
    if watchlist_file().exists():
        return False
    with Session(get_engine()) as s:
        rows = s.exec(select(WatchItemRow).order_by(WatchItemRow.id)).all()
    if not rows:
        return False
    _save_channels(
        [WatchChannel.model_validate(r.model_dump(include={"id", *CONFIG_FIELDS})) for r in rows]
    )
    return True


def load_channels() -> list[WatchChannel]:
    migrate_legacy()
    path = watchlist_file()
    return load_toml(path, WatchlistConfig).channels if path.exists() else []


def _sync() -> list[WatchChannel]:
    """Đưa database theo file: thêm kênh mới (chưa khởi tạo), cập nhật trường cấu hình, bỏ kênh
    đã xoá khỏi file cùng danh sách video đã biết của nó."""
    channels = load_channels()
    wanted = {c.id: c for c in channels}
    with Session(get_engine()) as s:
        rows = {r.id: r for r in s.exec(select(WatchItemRow)).all()}
        for row_id, row in rows.items():
            if row_id not in wanted:
                for k in s.exec(select(KnownVideoRow).where(KnownVideoRow.watch_item == row_id)):
                    s.delete(k)
                s.delete(row)
        for c in channels:
            row = rows.get(c.id)
            fields = c.model_dump(include=CONFIG_FIELDS)
            if row is None:
                s.add(WatchItemRow(id=c.id, created_at=_now(), **fields))
            elif any(getattr(row, k) != v for k, v in fields.items()):
                for k, v in fields.items():
                    setattr(row, k, v)
                s.add(row)
        try:
            s.commit()
        except IntegrityError:  # tiến trình khác vừa đồng bộ cùng lúc; kết quả như nhau
            s.rollback()
    return channels


def create_item(channel_id: str, handle: str | None, title: str, level: str) -> WatchItemRow:
    """Thêm kênh vào file, ở trạng thái chưa khởi tạo; bước thêm kênh chạy ở initialize()."""
    channels = load_channels()
    if any(c.channel_id == channel_id for c in channels):
        raise Duplicate(f"channel {channel_id} is already in the watchlist")
    with Session(get_engine()) as s:
        used = [*s.exec(select(WatchItemRow.id)).all(), *(c.id for c in channels)]
    n = max((int(i.removeprefix("w_")) for i in used), default=0) + 1
    item_id = f"w_{n:03d}"
    channel = WatchChannel(
        id=item_id, channel_id=channel_id, handle=handle, title=title, level=level
    )
    _save_channels([*channels, channel])
    _sync()
    return get_item(item_id)


def add_channel(text: str, level: str) -> WatchItemRow:
    """Thêm kênh từ link kênh, channel ID hoặc @handle."""
    target = parse_target(text)
    if target.kind not in (TargetKind.CHANNEL, TargetKind.HANDLE):
        raise ValueError("not a channel link, channel id or @handle")
    channel_id, title, handle = resolve(target)
    return create_item(channel_id, handle, title, level)


def get_item(item_id: str) -> WatchItemRow:
    _sync()
    with Session(get_engine()) as s:
        item = s.get(WatchItemRow, item_id)
    if item is None:
        raise NotFound(item_id)
    return item


def list_items() -> list[WatchItemRow]:
    _sync()
    with Session(get_engine()) as s:
        return list(s.exec(select(WatchItemRow).order_by(WatchItemRow.id)).all())


def update_item(item_id: str, **fields: object) -> WatchItemRow:
    """Trường cấu hình ghi vào file, trường trạng thái ghi vào database."""
    config = {k: v for k, v in fields.items() if k in CONFIG_FIELDS}
    if config:
        channels = load_channels()
        for i, c in enumerate(channels):
            if c.id == item_id:
                channels[i] = WatchChannel.model_validate({**c.model_dump(), **config})
                _save_channels(channels)
                break
        else:
            raise NotFound(item_id)
        _sync()
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
    channels = load_channels()
    if not any(c.id == item_id for c in channels):
        raise NotFound(item_id)
    _save_channels([c for c in channels if c.id != item_id])
    _sync()


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
