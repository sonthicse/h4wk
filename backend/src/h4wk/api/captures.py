"""API bằng chứng (T29): manifest, file gốc và kiểm tra toàn vẹn của một bản thu."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from h4wk.api.deps import current_actor
from h4wk.api.videos import _capture, _video_dir
from h4wk.core import audit
from h4wk.core.types import VN_TZ, VnDatetime
from h4wk.evidence.models import Manifest
from h4wk.evidence.verify import FileStatus, verify
from h4wk.evidence.writer import sha256_file

router = APIRouter(prefix="/api/videos/{video_id}/captures/{capture}", tags=["captures"])
ActorDep = Annotated[str, Depends(current_actor)]


class CaptureFile(BaseModel):
    path: str
    bytes: int
    sha256: str


class CaptureDetail(BaseModel):
    manifest: Manifest
    files: list[CaptureFile]


class FileResult(BaseModel):
    path: str
    status: FileStatus
    expected_sha256: str | None = None
    actual_sha256: str | None = None


class VerifyResult(BaseModel):
    checked_at: VnDatetime
    ok: bool
    files: list[FileResult]


def _dir(video_id: str, capture: str):
    d = _video_dir(video_id)
    return d / "captures" / _capture(d, capture)


def _manifest(video_id: str, capture: str) -> Manifest:
    path = _dir(video_id, capture) / "manifest.json"
    return Manifest.model_validate_json(path.read_text(encoding="utf-8"))


@router.get("")
def get_capture(video_id: str, capture: str) -> CaptureDetail:
    m = _manifest(video_id, capture)
    files = [
        CaptureFile(path=p, bytes=e.bytes, sha256=e.sha256) for p, e in sorted(m.files.items())
    ]
    return CaptureDetail(manifest=m, files=files)


@router.post("/verify")
def verify_capture(video_id: str, capture: str, actor: ActorDep) -> VerifyResult:
    cap_dir = _dir(video_id, capture)
    m = _manifest(video_id, capture)
    results = []
    for check in verify(cap_dir):
        entry = m.files.get(check.path)
        actual = None
        if check.status in (FileStatus.FAIL, FileStatus.UNEXPECTED):
            actual = sha256_file(cap_dir / check.path)
        results.append(
            FileResult(
                path=check.path,
                status=check.status,
                expected_sha256=entry.sha256 if entry else None,
                actual_sha256=actual,
            )
        )
    ok = all(r.status == FileStatus.OK for r in results)
    bad = [r.path for r in results if r.status != FileStatus.OK]
    audit.log(
        actor,
        "capture.verify",
        f"{video_id}/{capture}",
        {"ok": ok, "bad": bad},
        status="ok" if ok else "error",
    )
    return VerifyResult(checked_at=datetime.now(VN_TZ), ok=ok, files=results)


@router.get("/files/{path:path}", response_class=FileResponse)
def get_file(video_id: str, capture: str, path: str) -> FileResponse:
    """Tải file gốc; chỉ file có trong manifest (hoặc chính manifest.json)."""
    cap_dir = _dir(video_id, capture)
    m = _manifest(video_id, capture)
    if path != "manifest.json" and path not in m.files:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    target = cap_dir / path
    if not target.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    return FileResponse(target, filename=target.name)
