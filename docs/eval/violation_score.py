"""Chấm kết quả của violation_run.py theo đúng quy tắc của jev._content_violation: tổng xác
suất các danh mục vi phạm ≥ ngưỡng thì là vi phạm, danh mục là cái cao nhất.

python violation_score.py out.jsonl [ngưỡng]   # có ngưỡng thì in thêm các câu sai
Nhãn "?" (dữ liệu thật chưa gán nhãn) chỉ đếm số câu bị đánh dấu.
"""

import json
import sys
from collections import Counter

CATS = ("violence", "hate", "state_secret", "forgery")
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]


def predict(row, t):
    p = row["answers"].get("violation", {}).get("probabilities", {})
    total = sum(p.get(c, 0.0) for c in CATS)
    return (max(CATS, key=lambda c: p.get(c, 0.0)) if total >= t else "none"), total


for t in (0.5, 0.6, 0.7, 0.9):
    preds = [(r["label"], predict(r, t)[0]) for r in rows]
    if all(y == "?" for y, _ in preds):
        print(f"t={t}: flagged {sum(yh != 'none' for _, yh in preds)}/{len(preds)}")
        continue
    tp = sum(y != "none" and yh != "none" for y, yh in preds)
    fp = sum(y == "none" and yh != "none" for y, yh in preds)
    fn = sum(y != "none" and yh == "none" for y, yh in preds)
    per = Counter((y, yh) for y, yh in preds)
    cats = " ".join(
        f"{c}:{per[c, c]}/{sum(v for (y, _), v in per.items() if y == c)}" for c in CATS
    )
    print(f"t={t}: precision {tp}/{tp + fp}, recall {tp}/{tp + fn}, đúng danh mục {cats}")

if len(sys.argv) > 2:
    t = float(sys.argv[2])
    for r in rows:
        yh, total = predict(r, t)
        if yh != r["label"] and not (r["label"] == "?" and yh == "none"):
            print(f"  [{r['label']} -> {yh} {total:.2f}] {r['text'][:100]}")
