"""Checkpoint 6d: xử lý lại `1RUJ_6eruwA` từ đầu đến cuối với Jev thật trên bản sao dữ liệu.

Chạy từ `backend/` (một lần, chỉ khi lead cho phép):

    export UV_PROJECT_ENVIRONMENT=<repo>/backend/.venv PYTHONPATH=src
    uv run --no-sync python scripts/checkpoint_6d.py --check   # chỉ kiểm điều kiện, không gọi Jev
    uv run --no-sync python scripts/checkpoint_6d.py           # chạy thật

Bản sao nằm trong thư mục tạm mới; dữ liệu và cấu hình gốc chỉ được đọc. Chỉ bản thu (không có
`derived/`) được chép, nên media chạy lại từ video gốc (STT, keyframe, OCR, khớp ảnh, Jev).
Key `TYPESAFE_API_KEY` đọc từ `.env` của repo chính vào biến môi trường của tiến trình; không in ra.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

from dotenv import dotenv_values

VIDEO_ID = "1RUJ_6eruwA"
MARKER = "khung bo"  # "KHỦNG BỐ" sau khi bỏ dấu và hạ chữ thường
MAIN_REPO = Path("/home/ubuntu/h4wk")


def fold(text: str) -> str:
    """Bỏ dấu, hạ chữ thường để dò dòng OCR nhiễu dấu."""
    text = text.replace("Đ", "D").replace("đ", "d")
    plain = unicodedata.normalize("NFD", text)
    return "".join(c for c in plain if not unicodedata.combining(c)).lower()


def prepare(source: Path, config: Path, sandbox: Path) -> tuple[Path, Path]:
    """Chép bản thu, thực thể, mô hình và cấu hình sang `sandbox`; bỏ `derived/` để xử lý từ đầu."""
    data, conf = sandbox / "data", sandbox / "config"
    shutil.copytree(
        source / "videos" / VIDEO_ID / "captures", data / "videos" / VIDEO_ID / "captures"
    )
    for name in ("entities.json", "entities", "models"):
        origin = source / name
        if origin.is_dir():
            shutil.copytree(origin, data / name)
        elif origin.is_file():
            shutil.copy2(origin, data / name)
    conf.mkdir()
    for name in ("analysis.toml", "sources.toml"):
        if (config / name).is_file():
            shutil.copy2(config / name, conf / name)
    # Bản thu gốc chỉ đọc; bản sao phải ghi được để dọn dẹp và để hàng đợi mở file.
    for path in (data, conf):
        subprocess.run(["chmod", "-R", "u+w", str(path)], check=True)
    return data, conf


def summarize(data: Path, job_id: str) -> dict:
    """Số liệu nghiệm thu từ kết quả trong `data`; không đọc hay in nội dung gửi Jev."""
    from sqlmodel import Session

    from h4wk.core.db import JobRow, get_engine

    with Session(get_engine()) as s:
        job = s.get(JobRow, job_id)
    derived = data / "videos" / VIDEO_ID / "derived"
    run = job.run_id if job else None
    capture = job.capture if job else None
    out = derived / str(capture) / "analysis" / str(run)
    findings = json.loads((out / "findings.json").read_text(encoding="utf-8")) if run else []
    verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8")) if run else {}
    ocr = [f for f in findings if f["source_kind"] == "ocr" and MARKER in fold(f.get("quote", ""))]
    calls_path = data / "jev_calls.jsonl"
    calls = (
        [json.loads(x) for x in calls_path.read_text(encoding="utf-8").splitlines()]
        if calls_path.is_file()
        else []
    )
    return {
        "job": {"status": job.status, "step": job.step, "error": job.error} if job else None,
        "run_id": run,
        "findings": len(findings),
        "findings_by_source": dict(Counter(f["source_kind"] for f in findings)),
        "ocr_marker_findings": [
            {"id": f["id"], "frame": f.get("frame"), "category": f["category"]} for f in ocr
        ],
        "verdict": {k: verdict.get(k) for k in ("violation", "confidence", "model")},
        "jev_calls": {
            "lines": len(calls),
            "by_status": dict(Counter(c["status"] for c in calls)),
            "with_images": sum(1 for c in calls if c.get("images")),
            "retries_429": sum(c.get("retries_429") or 0 for c in calls),
            "input_tokens": sum(c["input_tokens"] for c in calls if type(c["input_tokens"]) is int),
            "output_tokens": sum(
                c["output_tokens"] for c in calls if type(c["output_tokens"]) is int
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=MAIN_REPO / "data")
    parser.add_argument("--config", type=Path, default=MAIN_REPO / "config")
    parser.add_argument("--env-file", type=Path, default=MAIN_REPO / ".env")
    parser.add_argument("--sandbox", type=Path, help="thư mục đích; mặc định tạo mới trong /tmp")
    parser.add_argument("--check", action="store_true", help="chỉ kiểm điều kiện, không chạy")
    args = parser.parse_args()

    if not (args.source / "videos" / VIDEO_ID / "captures").is_dir():
        print(f"missing captures for {VIDEO_ID} in {args.source}", file=sys.stderr)
        return 2
    key = os.environ.get("TYPESAFE_API_KEY") or dotenv_values(args.env_file).get("TYPESAFE_API_KEY")
    if not key:
        print("TYPESAFE_API_KEY is not set", file=sys.stderr)
        return 2
    if args.check:
        print("ok: captures present, TYPESAFE_API_KEY available (value not shown)")
        return 0

    sandbox = args.sandbox or Path(tempfile.mkdtemp(prefix="h4wk-cp6d."))
    if args.sandbox:
        args.sandbox.mkdir(parents=True, exist_ok=False)
    data, conf = prepare(args.source, args.config, sandbox)
    # Phải đặt trước khi import h4wk.jobs: hàng đợi Huey mở file trong thư mục dữ liệu lúc import.
    os.environ.update(H4WK_DATA_DIR=str(data), H4WK_CONFIG_DIR=str(conf), TYPESAFE_API_KEY=key)

    from h4wk.collectors.models import CollectLevel
    from h4wk.jobs import pipeline

    caps = sorted(p.name for p in (data / "videos" / VIDEO_ID / "captures").iterdir())
    job = pipeline.create_job(VIDEO_ID, VIDEO_ID, CollectLevel.FULL, False, "system:checkpoint-6d")
    pipeline._update(job.id, capture=caps[-1])
    # call_local chạy ngay trong tiến trình; media tự xếp analyze vào hàng đợi sandbox nên gọi tay.
    pipeline.media.call_local(job.id)
    if pipeline._update(job.id).status != "failed":
        pipeline.analyze.call_local(job.id)
    report = summarize(data, job.id)
    (sandbox / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"sandbox: {sandbox}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
