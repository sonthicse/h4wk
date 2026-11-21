import json
from unittest.mock import Mock

import pytest
from test_analysis_llm import _data

from h4wk.ai.gateway import GatewayError
from h4wk.analysis.models import Finding
from h4wk.analysis.verdict import decide
from h4wk.core.config_models import Route


def _finding(timeline, i, **fields):
    return Finding.model_validate(
        dict(
            id=f"f_{i:026d}",
            run_id="r_test",
            video_id=timeline.video_id,
            capture=timeline.capture,
            analyzer="static",
            analyzer_version="0.1.0",
            source_kind="description",
            entity="e_01",
            category="incitement",
            severity="high",
            confidence="likely",
            reason="",
            quote="q" * 400,
        )
        | fields
    )


def test_no_violations():
    data, timeline = _data()
    gateway = Mock()
    result, error = decide(
        data, [_finding(timeline, 0, category="neutral")], "r_test", timeline, gateway
    )
    assert result.violation == "no" and result.model is None and error is None
    gateway.complete_structured_with_route.assert_not_called()


@pytest.mark.parametrize("mode", ["mixed", "unknown", "gateway", "schema"])
def test_evidence_and_fallback(mode):
    data, timeline = _data()
    finding = _finding(timeline, 1)
    gateway = Mock()

    def respond(task, messages, schema):
        assert task == "analysis.video_verdict"
        if mode == "gateway":
            raise GatewayError("429 quota")
        ids = [_finding(timeline, 2).id] + ([finding.id] if mode == "mixed" else [])
        return schema(
            violation="yes",
            categories=["incitement"],
            confidence="likely",
            severity=None if mode == "schema" else "high",
            finding_ids=ids,
        ), Route(provider="gemini", model="fake")

    gateway.complete_structured_with_route.side_effect = respond
    result, error = decide(data, [finding], "r_test", timeline, gateway)
    assert result.finding_ids == [finding.id]
    if mode == "mixed":
        assert result.violation == "yes" and result.model.provider == "gemini" and error is None
    else:
        assert result.violation == "uncertain" and result.model is None and error


def test_payload_limits_and_order():
    data, timeline = _data()
    findings = [
        _finding(
            timeline,
            i,
            severity="high" if i < 100 else "medium",
            reason=f"Jev: incitement p={i % 100 / 100:.2f}",
        )
        for i in range(200)
    ]
    gateway = Mock()
    gateway.complete_structured_with_route.side_effect = GatewayError("offline")
    result, error = decide(data, findings, "r_test", timeline, gateway)
    _, messages, _ = gateway.complete_structured_with_route.call_args.args
    payload = json.loads(messages[1]["content"])
    assert payload["total_findings"] == 200
    assert [f["id"] for f in payload["findings"]] == [f.id for f in reversed(findings[40:100])]
    assert all(len(f["quote"]) == 300 for f in payload["findings"])
    assert error and result.finding_ids == [f.id for f in findings]


@pytest.mark.parametrize("args", [["demo"], ["--all"]])
def test_backfill_retries_fallback_and_preserves_success(data_dir, monkeypatch, args):
    from typer.testing import CliRunner

    from h4wk import cli
    from h4wk.analysis.models import VideoVerdict

    data, timeline = _data()
    video = data_dir / "videos" / "demo"
    capture = video / "captures" / timeline.capture
    derived = video / "derived" / timeline.capture
    run = derived / "analysis" / "r_test"
    capture.mkdir(parents=True)
    run.mkdir(parents=True)
    (capture / "normalized.json").write_text(data.model_dump_json(), encoding="utf-8")
    (derived / "timeline.json").write_text(timeline.model_dump_json(), encoding="utf-8")
    finding = _finding(timeline, 1)
    (run / "findings.json").write_text(f"[{finding.model_dump_json()}]", encoding="utf-8")
    gateway = Mock()
    monkeypatch.setattr(cli, "AIGateway", lambda: gateway)
    from h4wk.analysis.models import VerdictAnswer

    gateway.complete_structured_with_route.side_effect = GatewayError("offline")
    runner = CliRunner()
    assert runner.invoke(cli.app, ["verdict"]).exit_code == 2
    result = runner.invoke(cli.app, ["verdict", *args])
    assert result.exit_code == 0, result.exception
    path = run / "verdict.json"
    assert VideoVerdict.model_validate_json(path.read_bytes()).model is None
    gateway.complete_structured_with_route.side_effect = None
    gateway.complete_structured_with_route.return_value = (
        VerdictAnswer(
            violation="yes",
            categories=["incitement"],
            severity="high",
            confidence="likely",
            finding_ids=[finding.id],
        ),
        Route(provider="gemini", model="fake"),
    )
    result = runner.invoke(cli.app, ["verdict", *args])
    assert result.exit_code == 0, result.exception
    assert VideoVerdict.model_validate_json(path.read_bytes()).model.model == "fake"
    gateway.reset_mock()
    assert runner.invoke(cli.app, ["verdict", *args]).exit_code == 0
    gateway.complete_structured_with_route.assert_not_called()


def test_analyze_cli_creates_run(monkeypatch, data_dir):
    from typer.testing import CliRunner

    from h4wk import cli

    data, timeline = _data()
    video = data_dir / "videos" / timeline.video_id
    capture = video / "captures" / timeline.capture
    derived = video / "derived" / timeline.capture
    capture.mkdir(parents=True)
    derived.mkdir(parents=True)
    (capture / "normalized.json").write_text(data.model_dump_json(), encoding="utf-8")
    (derived / "timeline.json").write_text(timeline.model_dump_json(), encoding="utf-8")
    gateway = Mock()
    monkeypatch.setattr(cli, "AIGateway", lambda: gateway)
    result = CliRunner().invoke(cli.app, ["analyze", timeline.video_id])
    assert result.exit_code == 0, result.exception
    (path,) = derived.glob("analysis/*/verdict.json")
    assert path.with_name("findings.json").is_file()
    assert cli.VideoVerdict.model_validate_json(path.read_bytes()).run_id == path.parent.name


def test_analyze_all_stops_on_quota_without_replacing_run(monkeypatch, data_dir):
    from typer.testing import CliRunner

    from h4wk import cli
    from h4wk.analysis import runner
    from h4wk.jobs.pipeline import _latest_runs

    data, timeline = _data()
    for video_id in (timeline.video_id, "zz-next"):
        video = data_dir / "videos" / video_id
        capture = video / "captures" / timeline.capture
        derived = video / "derived" / timeline.capture
        old = derived / "analysis" / "r_00000000000000000000000000"
        capture.mkdir(parents=True)
        old.mkdir(parents=True)
        (capture / "normalized.json").write_text(data.model_dump_json(), encoding="utf-8")
        (derived / "timeline.json").write_text(timeline.model_dump_json(), encoding="utf-8")
        (old / "findings.json").write_text("[]", encoding="utf-8")
    before = _latest_runs(data_dir)
    gateway = Mock()
    gateway.complete_structured_with_route.side_effect = GatewayError("HTTP 429")
    monkeypatch.setattr(cli, "AIGateway", lambda: gateway)
    monkeypatch.setattr(runner.llm, "build_items", lambda *args: [object()])
    monkeypatch.setattr(
        runner.llm, "classify", lambda *args: gateway.complete_structured_with_route()
    )
    result = CliRunner().invoke(cli.app, ["analyze", "--all"])
    assert result.exit_code == 1, result.exception
    assert "429" in result.output
    assert _latest_runs(data_dir) == before
    gateway.complete_structured_with_route.assert_called_once()
