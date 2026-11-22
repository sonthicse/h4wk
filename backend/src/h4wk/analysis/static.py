import re
from dataclasses import dataclass
from pathlib import Path

from h4wk.analysis.models import Category
from h4wk.analysis.normalize import normalize

LEXICON_PATH = Path(__file__).parent / "lexicon" / "vi_insults.txt"
_HEADER = re.compile(r"^\[(?P<group>[^:\]]+):\s*(?P<category>\w+)\]$")


@dataclass(frozen=True)
class LexiconEntry:
    phrase: str
    group: str
    category: Category


def load_lexicon(path: Path = LEXICON_PATH) -> list[LexiconEntry]:
    entries: list[LexiconEntry] = []
    group, category = None, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if m := _HEADER.match(line):
            group, category = m["group"].strip(), Category(m["category"])
            continue
        if group is None or category is None:
            raise ValueError(f"phrase {line!r} is outside any group in {path}")
        entries.append(LexiconEntry(line, group, category))
    return entries


def find_insult(text: str, lexicon: list[LexiconEntry]) -> LexiconEntry | None:
    words = re.findall(r"\w+", normalize(text))
    for entry in lexicon:
        parts = re.findall(r"\w+", normalize(entry.phrase))
        if parts and any(words[i : i + len(parts)] == parts for i in range(len(words))):
            return entry
    return None
