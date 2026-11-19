"""Phân loại đầu vào người dùng dán vào: link hoặc ID video, kênh, @handle, playlist."""

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import parse_qs, urlparse

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
PLAYLIST_ID = re.compile(r"^(PL|UU|LL|FL|OL)[A-Za-z0-9_-]{10,}$")
HANDLE = re.compile(r"^@[A-Za-z0-9._-]{3,30}$")
HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


class TargetKind(StrEnum):
    VIDEO = "video"
    CHANNEL = "channel"
    HANDLE = "handle"
    PLAYLIST = "playlist"


@dataclass(frozen=True)
class Target:
    kind: TargetKind
    id: str

    @property
    def url(self) -> str:
        return {
            TargetKind.VIDEO: f"https://www.youtube.com/watch?v={self.id}",
            TargetKind.CHANNEL: f"https://www.youtube.com/channel/{self.id}",
            TargetKind.HANDLE: f"https://www.youtube.com/{self.id}",
            TargetKind.PLAYLIST: f"https://www.youtube.com/playlist?list={self.id}",
        }[self.kind]


def _bare(text: str) -> Target | None:
    for pattern, kind in [
        (CHANNEL_ID, TargetKind.CHANNEL),
        (PLAYLIST_ID, TargetKind.PLAYLIST),
        (HANDLE, TargetKind.HANDLE),
        (VIDEO_ID, TargetKind.VIDEO),
    ]:
        if pattern.match(text):
            return Target(kind, text)
    return None


def parse_target(text: str) -> Target:
    text = text.strip()
    if bare := _bare(text):
        return bare
    url = urlparse(text if "://" in text else f"https://{text}")
    if url.hostname not in HOSTS:
        raise ValueError(f"not a recognised YouTube link: {text!r}")
    parts = [p for p in url.path.split("/") if p]
    query = parse_qs(url.query)
    candidates: list[tuple[str, TargetKind]] = []
    if url.hostname == "youtu.be" and parts:
        candidates.append((parts[0], TargetKind.VIDEO))
    if "v" in query:  # watch?v=…&list=… vẫn là một video
        candidates.append((query["v"][0], TargetKind.VIDEO))
    if parts and parts[0] in {"shorts", "live", "embed"} and len(parts) > 1:
        candidates.append((parts[1], TargetKind.VIDEO))
    if parts and parts[0] == "channel" and len(parts) > 1:
        candidates.append((parts[1], TargetKind.CHANNEL))
    if parts and parts[0].startswith("@"):
        candidates.append((parts[0], TargetKind.HANDLE))
    if "list" in query:
        candidates.append((query["list"][0], TargetKind.PLAYLIST))
    for ident, kind in candidates:
        t = _bare(ident)
        if t is not None and t.kind == kind:
            return t
    raise ValueError(f"no video, channel or playlist found in: {text!r}")
