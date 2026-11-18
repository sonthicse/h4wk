"""Chuẩn hóa và tìm tên trong văn bản."""

import re
import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def _one_edit(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return a[i + 1:] == b[i + 1:] if len(a) == len(b) else a[i:] == b[i + 1:]
    return True


def matches_name(text: str, names: list[str], abbreviations: list[str]) -> bool:
    words = re.findall(r"\w+", normalize(text))
    if any(normalize(abbr) in words for abbr in abbreviations if abbr.strip()):
        return True
    for name in names:
        parts = re.findall(r"\w+", normalize(name))
        if not parts:
            continue
        for i in range(len(words) - len(parts) + 1):
            if all(a == b or (len(a) >= 4 and _one_edit(a, b))
                   for a, b in zip(parts, words[i:i + len(parts)], strict=True)):
                return True
    return False
