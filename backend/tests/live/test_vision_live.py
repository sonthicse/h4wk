"""Mô tả khung hình bằng VLM thật trên 3 khung mẫu biết trước dấu hiệu (T21).

Khóa API đọc từ .env ở thư mục gốc repo hoặc biến môi trường (data/secrets.json
không có vì conftest đặt data_dir tạm)."""

from pathlib import Path

import pytest

from h4wk.ai.config import AI_CONFIG_PATH
from h4wk.ai.gateway import AIGateway
from h4wk.media import vision

pytestmark = pytest.mark.live
FRAMES = (
    Path(__file__).resolve().parents[1]
    / "fixtures/captures/h4wkDemo001/derived/20261118T160000/frames"
)
HANDCUFFS = "000025.jpg"  # ảnh chế: chữ TỘI PHẠM đè lên mặt, vẽ còng tay
INSULT_TEXT = "000015.jpg"  # chữ lớn "TRẦN VĂN MẪU LỪA ĐẢO"
NORMAL = "000032.jpg"  # ảnh hoa văn đổi màu, không có dấu hiệu


def test_vision_live(monkeypatch, tmp_path):
    path = (
        AI_CONFIG_PATH if AI_CONFIG_PATH.exists() else AI_CONFIG_PATH.with_suffix(".toml.example")
    )
    gateway = AIGateway(config_path=path, log_dir=tmp_path)
    monkeypatch.setattr(vision, "AIGateway", lambda: gateway)
    names = [HANDCUFFS, INSULT_TEXT, NORMAL]
    images = [(f"frames/{name}", FRAMES / name) for name in names]
    result = vision.describe_images(images, tmp_path / "vision.json")
    assert set(result) == {file for file, _ in images}, "VLM không mô tả đủ 3 khung"
    cues = [c.lower() for c in result[f"frames/{HANDCUFFS}"].offensive_cues]
    assert any("còng" in c or "handcuff" in c for c in cues), cues
    assert result[f"frames/{INSULT_TEXT}"].offensive_cues
    assert result[f"frames/{NORMAL}"].offensive_cues == []
