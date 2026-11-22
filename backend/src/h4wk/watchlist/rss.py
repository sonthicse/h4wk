import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

from h4wk.core.types import VN_TZ

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


@dataclass(frozen=True)
class FeedEntry:
    video_id: str
    title: str
    published_at: datetime | None


def parse_feed(xml: bytes) -> list[FeedEntry]:
    root = ET.fromstring(xml)
    out = []
    for entry in root.findall("a:entry", _NS):
        vid = entry.findtext("yt:videoId", namespaces=_NS)
        if not vid:
            continue
        published = entry.findtext("a:published", namespaces=_NS)
        out.append(
            FeedEntry(
                video_id=vid,
                title=entry.findtext("a:title", default="", namespaces=_NS),
                published_at=datetime.fromisoformat(published).astimezone(VN_TZ)
                if published
                else None,
            )
        )
    return out


def fetch_feed(channel_id: str, timeout: float = 15) -> list[FeedEntry]:
    req = urllib.request.Request(FEED_URL.format(channel_id), headers={"User-Agent": "h4wk"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL cố định)
        return parse_feed(resp.read())
