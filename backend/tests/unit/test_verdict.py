import pytest
from _analysis_sample import _data

from h4wk.analysis.models import Finding
from h4wk.analysis.verdict import decide


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


def test_no_violations_and_other_runs_ignored():
    _, timeline = _data()
    other = _finding(timeline, 0, run_id="r_other", confidence="highly_likely")
    neutral = _finding(timeline, 1, category="neutral")
    result = decide([other, neutral], "r_test", timeline)
    assert result.violation == "no"
    assert result.confidence == "highly_likely" and result.summary == "Không có nghi vấn vi phạm."
    assert result.categories == [] and result.finding_ids == []


@pytest.mark.parametrize(
    ("confidences", "expected"),
    [
        (["highly_likely"], "yes"),
        (["likely", "highly_likely"], "yes"),
        (["likely", "unverified"], "uncertain"),
        (["unverified"], "uncertain"),
    ],
)
def test_violation_by_confidence(confidences, expected):
    _, timeline = _data()
    findings = [_finding(timeline, i, confidence=c) for i, c in enumerate(confidences)]
    assert decide(findings, "r_test", timeline).violation == expected


def test_summary_categories_and_top_confidence():
    _, timeline = _data()
    findings = [
        _finding(timeline, 0, category="insult", severity="medium", confidence="likely"),
        _finding(timeline, 1, category="insult", severity="low"),
        _finding(timeline, 2, category="incitement", severity="high", confidence="highly_likely"),
        _finding(timeline, 3, category="insult", severity="low"),
    ]
    result = decide(findings, "r_test", timeline)
    assert result.categories == ["insult", "incitement"]
    assert result.severity == "high"
    assert result.confidence == "highly_likely"  # của nghi vấn xếp đầu
    assert result.finding_ids[0] == findings[2].id
    assert (
        result.summary
        == "4 nghi vấn vi phạm; danh mục: insult (3), incitement (1); mức cao nhất: high."
    )


def test_ten_ids_ranked_by_severity_then_jev_probability():
    _, timeline = _data()
    findings = [
        _finding(
            timeline,
            i,
            severity="high" if i < 100 else "medium",
            reason=f"Jev: incitement p={i % 100 / 100:.2f}",
        )
        for i in range(200)
    ]
    result = decide(findings, "r_test", timeline)
    assert result.finding_ids == [f.id for f in reversed(findings[90:100])]
    assert result.summary.startswith("200 nghi vấn vi phạm")


@pytest.mark.parametrize("args", [["demo"], ["--all"]])
def test_backfill_writes_once_and_force_rewrites(data_dir, args):
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
    finding = _finding(timeline, 1, confidence="highly_likely")
    (run / "findings.json").write_text(f"[{finding.model_dump_json()}]", encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(cli.app, ["verdict"]).exit_code == 2
    result = runner.invoke(cli.app, ["verdict", *args])
    assert result.exit_code == 0, result.exception
    path = run / "verdict.json"
    first = VideoVerdict.model_validate_json(path.read_bytes())
    assert first.violation == "yes"
    # Chạy lại không ghi đè: đổi nội dung rồi kiểm tra còn nguyên.
    path.write_text(first.model_copy(update={"summary": "giữ"}).model_dump_json(), encoding="utf-8")
    assert runner.invoke(cli.app, ["verdict", *args]).exit_code == 0
    assert VideoVerdict.model_validate_json(path.read_bytes()).summary == "giữ"
    assert runner.invoke(cli.app, ["verdict", *args, "--force"]).exit_code == 0
    assert VideoVerdict.model_validate_json(path.read_bytes()).summary.startswith("1 nghi vấn")


def test_analyze_cli_creates_run(data_dir):
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
    result = CliRunner().invoke(cli.app, ["analyze", timeline.video_id])
    assert result.exit_code == 0, result.exception
    (path,) = derived.glob("analysis/*/verdict.json")
    assert path.with_name("findings.json").is_file()
    assert cli.VideoVerdict.model_validate_json(path.read_bytes()).run_id == path.parent.name


def test_analyze_all_stops_on_quota_without_replacing_run(monkeypatch, data_dir):
    from typer.testing import CliRunner

    from h4wk import cli
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
    from h4wk.jobs import pipeline

    monkeypatch.setattr(pipeline.runner, "analyze", lambda *args, **kwargs: ([], [], "HTTP 429"))
    result = CliRunner().invoke(cli.app, ["analyze", "--all"])
    assert result.exit_code == 1, result.exception
    assert "429" in result.output
    assert _latest_runs(data_dir) == before
