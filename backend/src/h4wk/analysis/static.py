"""Kiểm tra từ ngữ xúc phạm trong văn bản."""

import re
from pathlib import Path

from h4wk.analysis.normalize import normalize


def contains_insult(text: str, insults: list[str]) -> bool:
    words = re.findall(r"\w+", normalize(text))
    for insult in insults:
        parts = re.findall(r"\w+", normalize(insult))
        if parts and any(words[i:i + len(parts)] == parts for i in range(len(words))):
            return True
    return False


def load_insults() -> list[str]:
    path = Path(__file__).parent / "lexicon" / "vi_insults.txt"
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
