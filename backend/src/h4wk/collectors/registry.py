from collections.abc import Callable

from h4wk.collectors.base import Collector
from h4wk.collectors.providers import supadata, youtube_api, ytdlp

COLLECTORS: dict[str, Callable[[], Collector]] = {
    "ytdlp": ytdlp.from_config,
    "youtube_api": youtube_api.from_config,
    "supadata": supadata.from_config,
}
