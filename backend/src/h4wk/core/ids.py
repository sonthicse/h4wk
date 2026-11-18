"""Sinh ULID: 48 bit thời gian (ms) + 80 bit ngẫu nhiên, mã hoá Crockford base32 (26 ký tự).
Sắp theo chuỗi cũng là sắp theo thời gian tạo."""

import secrets
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    return "".join(_ALPHABET[(value >> (5 * i)) & 31] for i in reversed(range(26)))
