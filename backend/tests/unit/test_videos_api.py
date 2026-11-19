"""API đọc video đã thu, dùng bản thu mẫu của T44."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from h4wk.analysis.models import Finding
from h4wk.core.db import FindingRow, get_engine

SAMPLE = Path(__file__).parents[1] / "fixtures" / "captures" / "h4wkDemo001"
CAP = "20261118T160000"
VID = "h4wkDemo001"


@pytest.fixture
def sample(client: TestClient, data_dir: Path) -> None:
    shutil.copytree(SAMPLE, data_dir / "videos" / VID)
    path = SAMPLE / "derived" / CAP / "analysis" / "r_20261118T160500" / "findings.json"
    with Session(get_engine()) as s:
        for raw in json.loads(path.read_text(encoding="utf-8")):
            f = Finding.model_validate(raw)
            s.add(
                FindingRow(
                    id=f.id,
                    video_id=f.video_id,
                    capture=f.capture,
                    run_id=f.run_id,
                    data=f.model_dump_json(),
                )
            )
        s.commit()


def test_list_and_detail(client: TestClient, sample) -> None:
    videos = client.get("/api/videos").json()
    assert [v["id"] for v in videos] == [VID]
    assert videos[0]["latest_capture"] == CAP and videos[0]["title"]
    assert sum(videos[0]["findings"].values()) > 0
    detail = client.get(f"/api/videos/{VID}").json()
    assert detail["video"]["id"] == VID
    cap = detail["captures"][0]
    assert cap["id"] == CAP and cap["level"] == "full"
    assert cap["collected_at"].endswith("+07:00")


def test_timeline_transcripts_comments(client: TestClient, sample) -> None:
    timeline = client.get(f"/api/videos/{VID}/timeline").json()
    assert timeline["video_id"] == VID and timeline["segments"]
    assert client.get(f"/api/videos/{VID}/transcripts").json()[0]["segments"]
    assert isinstance(client.get(f"/api/videos/{VID}/comments").json(), list)


def test_media_supports_range_and_frames(client: TestClient, sample) -> None:
    r = client.get(f"/api/videos/{VID}/media", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100
    frame = sorted((SAMPLE / "derived" / CAP / "frames").glob("*.jpg"))[0].name
    r = client.get(f"/api/videos/{VID}/frames/{frame}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"


def test_not_found_and_traversal(client: TestClient, sample) -> None:
    assert client.get("/api/videos/khongco").status_code == 404
    assert client.get(f"/api/videos/{VID}/timeline?capture=20990101T000000").status_code == 404
    assert client.get(f"/api/videos/{VID}/frames/..%2Fanalysis").status_code == 404
    assert client.get("/api/videos/..%2F..%2Findex.db").status_code == 404


def test_empty_when_nothing_collected(client: TestClient) -> None:
    assert client.get("/api/videos").json() == []


# ----------------------------------------------------------- T29: bằng chứng


def test_capture_manifest_and_download(client: TestClient, sample) -> None:
    detail = client.get(f"/api/videos/{VID}/captures/{CAP}").json()
    assert detail["manifest"]["level"] == "full"
    first = detail["files"][0]
    r = client.get(f"/api/videos/{VID}/captures/{CAP}/files/{first['path']}")
    assert r.status_code == 200 and len(r.content) == first["bytes"]
    assert client.get(f"/api/videos/{VID}/captures/{CAP}/files/../../index.db").status_code == 404


def test_verify_reports_changed_byte(client: TestClient, sample, data_dir: Path) -> None:
    url = f"/api/videos/{VID}/captures/{CAP}/verify"
    r = client.post(url).json()
    assert r["ok"] and {f["status"] for f in r["files"]} == {"OK"}
    cap_dir = data_dir / "videos" / VID / "captures" / CAP
    target = cap_dir / "normalized.json"
    target.chmod(0o644)
    data = bytearray(target.read_bytes())
    data[10] ^= 1
    target.write_bytes(bytes(data))
    r = client.post(url).json()
    bad = [f for f in r["files"] if f["status"] != "OK"]
    assert not r["ok"] and [f["path"] for f in bad] == ["normalized.json"]
    assert bad[0]["status"] == "FAIL" and bad[0]["actual_sha256"] != bad[0]["expected_sha256"]
    log = (data_dir / "log" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(log[-1])["action"] == "capture.verify"
