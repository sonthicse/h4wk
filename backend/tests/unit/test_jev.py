import io
import json
from urllib.error import HTTPError

import pytest
from test_analysis_llm import ENTITY, INSULT, _data

from h4wk.analysis import jev, runner
from h4wk.core.config_models import JevSettings


@pytest.mark.parametrize(
    ("target", "probability", "kept"),
    [("e_01", 0.5, True), ("none", 0.9, False), ("e_01", 0.49, False)],
)
def test_classify(monkeypatch, target, probability, kept):
    data, timeline = _data()
    monkeypatch.setattr(jev.secrets, "get", lambda name: "test-key")
    states = []
    second = ENTITY.model_copy(
        update={
            "id": "e_02",
            "name": "Mẫu hai",
            "aliases": ["Tên khác"],
            "abbreviations": ["MH"],
            "description": "Mô tả mẫu",
        }
    )

    def reply(request, timeout):
        assert (
            request.full_url == jev.URL and request.get_header("Authorization") == "Bearer test-key"
        )
        payload = json.loads(request.data)
        states.append(payload["state"])
        questions = payload["questions"]
        assert set(questions) == {"category", "severity", "is_attack", "target"}
        criteria = questions["target"]["criteria"]
        assert set(criteria) == {"e_01", "e_02", "none"}
        assert criteria["e_02"] == "Mẫu hai, Tên khác, MH, Mô tả mẫu"
        assert set(questions["category"]["criteria"]["insult"]) == {"what", "examples"}
        return io.BytesIO(
            json.dumps(
                {
                    "model": "jev-test",
                    "answers": {
                        "category": {"probabilities": {"insult": 0.8}},
                        "is_attack": {"noul": probability},
                        "target": {"choice": target},
                        "severity": {"score": 1.5},
                    },
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(jev.urllib.request, "urlopen", reply)
    findings, records, error = jev.classify(
        data, timeline, [ENTITY, second], [], "r_x", JevSettings()
    )
    assert error is None
    assert records and all(r["kept"] == kept for r in records)
    assert any(s.get("parent_comment") for s in states)
    assert {s["source_type"] for s in states} == {"YouTube comment", "speech transcript segment"}
    for state in states:
        assert "Mẫu hai, Tên khác, MH, Mô tả mẫu" in state["protected_targets"]
        assert state["text"]
        assert "video_title" in state
        if state["source_type"] == "speech transcript segment":
            assert {"speech_before", "speech_after"} <= state.keys()
        else:
            assert "speech_before" not in state and "speech_after" not in state
    if kept:
        assert {f.source_kind for f in findings} == {"speech", "comment"}
        assert all(
            f.entity == target and f.category == "insult" and f.severity == "high" for f in findings
        )
    else:
        assert not findings


def test_retry(monkeypatch):
    calls = []
    delays = []

    def reply(request, timeout):
        calls.append(request)
        if len(calls) <= 2:
            raise HTTPError(jev.URL, 429, "", {"retry-after": "0.5"}, None)
        return io.BytesIO(b'{"model":"jev-test"}')

    monkeypatch.setattr(jev.urllib.request, "urlopen", reply)
    monkeypatch.setattr(jev.time, "sleep", delays.append)
    assert jev._call("test-key", {}, {}) == {"model": "jev-test"}
    assert delays == [0.5, 0.5]


@pytest.mark.parametrize("key", [None, "test-key"])
def test_failure_keeps_static(monkeypatch, tmp_path, key):
    monkeypatch.setattr(jev.secrets, "get", lambda name: key)

    def fail(request, timeout):
        assert key
        raise HTTPError(jev.URL, 500, "", {}, None)

    monkeypatch.setattr(jev.urllib.request, "urlopen", fail)
    data, timeline = _data()
    _, findings, error = runner.analyze(
        data, timeline, [ENTITY], INSULT, "r_x", tmp_path, jev_settings=JevSettings()
    )
    assert findings and {f.analyzer for f in findings} == {"static"}
    assert error.startswith("jev:")
    assert ("HTTP 500" if key else "TYPESAFE_API_KEY is not set") in error
