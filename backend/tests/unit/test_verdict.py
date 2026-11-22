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
