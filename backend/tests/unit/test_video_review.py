from datetime import datetime

from h4wk.analysis.models import VideoVerdict
from h4wk.core.reindex import reindex
from h4wk.core.types import VN_TZ


def _run(root, vid, capture, run, violation="yes"):
    path = root / "videos" / vid / "derived" / capture / "analysis" / run
    path.mkdir(parents=True)
    (path / "findings.json").write_text("[]", encoding="utf-8")
    fields = dict(categories=["insult"], severity="low", finding_ids=[f"f_{0:026d}"])
    verdict = VideoVerdict(
        video_id=vid,
        capture=capture,
        run_id=run,
        violation=violation,
        confidence="likely",
        at=datetime.now(VN_TZ),
        **(fields if violation == "yes" else {}),
    )
    (path / "verdict.json").write_text(verdict.model_dump_json(), encoding="utf-8")


def test_video_review_lifecycle(client, data_dir):
    _run(data_dir, "one", "20261120T120000", "r_first")
    _run(data_dir, "two", "20261120T120000", "r_no", "no")
    queue = "/api/review/videos"
    decision = "/api/videos/one/decision"
    assert [i["video"]["id"] for i in client.get(queue).json()] == ["one"]
    before = client.get("/api/dashboard").json()["videos_by_review_status"]
    rejected = client.post(decision, json={"status": "rejected", "run_id": "r_first"})
    assert rejected.status_code == 422 and rejected.json()["detail"] == "Reject needs a note"
    confirmed = client.post(decision, json={"status": "confirmed", "run_id": "r_first"})
    assert confirmed.status_code == 200, confirmed.text
    assert client.get(queue, params={"status": "confirmed"}).json()[0]["decisions"] == [
        confirmed.json()
    ]
    after = client.get("/api/dashboard").json()["videos_by_review_status"]
    assert after["unreviewed"] == before["unreviewed"] - 1
    assert after["confirmed"] == before["confirmed"] + 1
    _run(data_dir, "one", "20261121T120000", "r_second")
    assert client.get("/api/videos/one/verdict").json()["status"] == "unreviewed"
    assert client.get("/api/videos/missing/verdict").status_code == 404
    stale = client.post(decision, json={"status": "confirmed", "run_id": "r_first"})
    assert stale.status_code == 409
    assert len((data_dir / "reviews.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert "review.decide_video" in (data_dir / "log" / "audit.jsonl").read_text(encoding="utf-8")
    old_and_new = client.get(queue, params={"latest_only": False}).json()
    assert [i["status"] for i in old_and_new] == ["unreviewed", "confirmed"]
    assert reindex().decisions == 1
    from h4wk.review.videos import queue as load_queue

    assert [i.model_dump(mode="json") for i in load_queue(latest_only=False)] == old_and_new
