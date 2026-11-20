import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from h4wk.analysis.evaluation import Unit, collect_units, markdown_table, place_of, sample, score
from h4wk.analysis.models import EntityHit, ModelRef
from h4wk.analysis.runner import analyze
from h4wk.cli import app
from h4wk.collectors.models import Normalized
from h4wk.core.entities import Entity
from h4wk.media.timeline import Timeline

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001"
CAPTURE = "20261118T160000"


def _hit(**kw) -> EntityHit:
    return EntityHit(entity="e_01", **kw)


def test_place_of() -> None:
    assert place_of(_hit(via="comment", comment_id="c1")) == ("c1", "comment")
    assert place_of(_hit(via="speech", segment_id="seg_0001")) == ("seg_0001", "segment")
    thumbs = {"a/maxres.jpg"}
    assert place_of(_hit(via="thumbnail", frame="a/maxres.jpg"), thumbs) == (
        "a/maxres.jpg",
        "thumbnail",
    )
    assert place_of(_hit(via="ref_image", frame="a/maxres.jpg"), thumbs) == (
        "a/maxres.jpg",
        "thumbnail",
    )
    assert place_of(_hit(via="ref_image", frame="frames/000009.jpg"), thumbs) == (
        "frames/000009.jpg",
        "frame",
    )
    assert place_of(_hit(via="title")) == ("title", "title")


def _row(label: str, static: str, llm: str) -> dict:
    return {"label": label, "static": static, "llm": llm}


def test_score_by_hand() -> None:
    rows = [
        _row("1", "1", "1"),
        _row("1", "1", "0"),
        _row("0", "1", "0"),
        _row("1", "0", "1"),
        _row("0", "0", "0"),
        _row("", "1", "1"),  # chưa gán nhãn thì bỏ qua
    ]
    static = score(rows)["static"]
    assert (static["tp"], static["fp"], static["fn"], static["tn"], static["n"]) == (2, 1, 1, 1, 5)
    assert round(static["precision"], 2) == 0.67
    assert round(static["recall"], 2) == 0.67
    assert "0.67" in markdown_table(score(rows))


def test_score_without_positive_predictions() -> None:
    result = score([_row("1", "0", "0"), _row("0", "0", "0")])["static"]
    assert result["precision"] is None
    assert result["recall"] == 0
    assert result["f1"] is None
    assert "–" in markdown_table({"static": result})


def _units(positives: int, negatives: int) -> list[Unit]:
    def make(i: int, positive: bool) -> Unit:
        return Unit("v", "c", "r", f"p{i:03d}", "segment", "e_01", "t", positive, False)

    return [make(i, True) for i in range(positives)] + [
        make(100 + i, False) for i in range(negatives)
    ]


def test_sample_takes_all_positives() -> None:
    chosen = sample(_units(10, 50), n=50, seed=1)
    assert sum(u.static for u in chosen) == 10
    assert len(chosen) == 50
    assert [u.unit_id for u in chosen] == [f"u_{i:03d}" for i in range(1, 51)]
    again = sample(_units(10, 50), n=50, seed=1)
    assert [u.place for u in again] == [u.place for u in chosen]


def test_sample_caps_positives_at_half() -> None:
    chosen = sample(_units(40, 40), n=50, seed=0)
    assert sum(u.static for u in chosen) == 25
    assert len(chosen) == 50


def _build_capture(data_dir: Path, video: str, with_llm: bool) -> None:
    src = FIXTURE
    cap = data_dir / "videos" / video / "captures" / CAPTURE
    der = data_dir / "videos" / video / "derived" / CAPTURE
    cap.mkdir(parents=True)
    der.mkdir(parents=True)
    shutil.copy(src / "captures" / CAPTURE / "normalized.json", cap / "normalized.json")
    shutil.copy(src / "derived" / CAPTURE / "timeline.json", der / "timeline.json")
    run = der / "analysis" / "01RUN"
    run.mkdir(parents=True)
    data = Normalized.model_validate_json((cap / "normalized.json").read_text(encoding="utf-8"))
    timeline = Timeline.model_validate_json((der / "timeline.json").read_text(encoding="utf-8"))
    hits, findings, _ = analyze(
        data, timeline, [Entity(id="e_01", name="Trần Văn Mẫu")], None, "r", run
    )
    llm_findings = [
        f.model_copy(update={"analyzer": "llm", "model": ModelRef(provider="p", model="m")})
        for f in findings
        if f.comment_id == "c1"
    ]
    out = [f.model_dump(mode="json", by_alias=True) for f in llm_findings]
    # runner đã bỏ nghi vấn tĩnh bị LLM thay: findings.json chỉ còn mục LLM và các mục tĩnh khác
    rest = [f.model_dump(mode="json", by_alias=True) for f in findings if f.comment_id != "c1"]
    (run / "findings.json").write_text(json.dumps(out + rest), encoding="utf-8")
    if with_llm:
        (run / "llm.json").write_text("[]", encoding="utf-8")


def _entities(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "entities.json").write_text(
        json.dumps([{"id": "e_01", "name": "Trần Văn Mẫu"}]), encoding="utf-8"
    )


def test_collect_units(data_dir: Path) -> None:
    _entities(data_dir)
    _build_capture(data_dir, "vidA", with_llm=True)
    _build_capture(data_dir, "vidB", with_llm=False)
    units = collect_units(data_dir)
    assert {u.video_id for u in units} == {"vidA"}  # vidB chưa chạy LLM
    by_place = {u.place: u for u in units}
    assert by_place["c1"].llm and by_place["c1"].static  # static tính lại, không đọc findings.json
    assert by_place["c1"].kind == "comment"
    assert "lừa đảo" in by_place["c1"].text
    segment = next(u for u in units if u.kind == "segment")
    assert segment.static and not segment.llm
    assert "Trần Văn Mẫu" in segment.text


def test_cli_sample_and_score(data_dir: Path, tmp_path: Path) -> None:
    _entities(data_dir)
    _build_capture(data_dir, "vidA", with_llm=True)
    out = tmp_path / "eval"
    runner = CliRunner()
    first = runner.invoke(app, ["eval", "sample", "--out", str(out)])
    assert first.exit_code == 0, first.output
    assert (out / "labels.csv").is_file() and (out / "predictions.csv").is_file()
    header = (out / "labels.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "static" not in header and "llm" not in header
    assert runner.invoke(app, ["eval", "sample", "--out", str(out)]).exit_code == 1
    assert runner.invoke(app, ["eval", "sample", "--out", str(out), "--force"]).exit_code == 0

    import csv

    with (out / "labels.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["label"] = "1"
    with (out / "labels.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = runner.invoke(app, ["eval", "score", "--dir", str(out)])
    assert result.exit_code == 0, result.output
    assert "| static |" in result.output
    assert "unlabelled: 0" in result.output


def test_score_f1_zero_when_no_true_positive() -> None:
    zero = score([_row("0", "1", "0"), _row("1", "0", "0")])["static"]
    assert (zero["tp"], zero["fp"], zero["fn"]) == (0, 1, 1)
    assert zero["precision"] == 0 and zero["recall"] == 0 and zero["f1"] == 0.0


def test_llm_finding_without_hit_becomes_unit(data_dir: Path) -> None:
    _entities(data_dir)
    _build_capture(data_dir, "vidA", with_llm=True)
    run = data_dir / "videos/vidA/derived" / CAPTURE / "analysis/01RUN"
    findings = json.loads((run / "findings.json").read_text(encoding="utf-8"))
    extra = next(f for f in findings if f["analyzer"] == "llm")
    extra.update(
        id="f_" + "0" * 26,
        comment_id=None,
        source_kind="speech",
        segment_id="seg_0004",
        start=1.0,
        end=2.0,
        triggers=[{"via": "speech", "segment_id": "seg_0004"}],
    )
    findings.append(extra)
    (run / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    hits = json.loads((run / "hits.json").read_text(encoding="utf-8"))
    assert all(h.get("segment_id") != "seg_0004" for h in hits)  # đoạn này không có hit
    unit = next(u for u in collect_units(data_dir) if u.place == "seg_0004")
    assert unit.llm and not unit.static and unit.kind == "segment"
