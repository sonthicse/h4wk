"""Tầng LLM của analysis chạy với nhà cung cấp thật trên bản thu mẫu.

Khóa API đọc từ .env ở thư mục gốc repo hoặc biến môi trường (data/secrets.json
không có vì conftest đặt data_dir tạm)."""

from pathlib import Path

import pytest

from h4wk.ai.config import AI_CONFIG_PATH
from h4wk.ai.gateway import AIGateway
from h4wk.analysis import runner
from h4wk.collectors.models import Normalized
from h4wk.core.entities import Entity
from h4wk.media.timeline import Timeline

pytestmark = pytest.mark.live
SAMPLE = Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001"
CAPTURE = "20261118T160000"


def test_analysis_llm_live(tmp_path):
    path = (
        AI_CONFIG_PATH if AI_CONFIG_PATH.exists() else AI_CONFIG_PATH.with_suffix(".toml.example")
    )
    data = Normalized.model_validate_json(
        (SAMPLE / "captures" / CAPTURE / "normalized.json").read_text(encoding="utf-8")
    )
    timeline = Timeline.model_validate_json(
        (SAMPLE / "derived" / CAPTURE / "timeline.json").read_text(encoding="utf-8")
    )
    entity = Entity(id="e_01", name="Trần Văn Mẫu", aliases=["Mẫu Ca"], abbreviations=["TVM"])
    gateway = AIGateway(config_path=path, log_dir=tmp_path)
    _, findings, error = runner.analyze(
        data, timeline, [entity], None, "r_live", tmp_path / "out", gateway=gateway
    )
    assert error is None
    assert any(f.analyzer == "llm" for f in findings)
