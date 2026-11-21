"""Phân loại lời nói và bình luận qua Jev."""

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from h4wk.analysis.models import Finding, ModelRef, Trigger
from h4wk.core import secrets
from h4wk.core.ids import new_ulid

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
VIOLATIONS = {
    "insult": "insults, slanders, curses or humiliates the target",
    "unsupported_accusation": "accuses the target of wrongdoing or crimes without evidence",
    "fabrication": "distorts facts or spreads made-up information about the target",
    "incitement": "incites hatred, division, protest or violence against the target",
    "state_secret": "reveals state secrets",
}


def _call(key, state, questions):
    request = urllib.request.Request(
        URL,
        data=json.dumps({"model": MODEL, "state": state, "questions": questions}).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            with error:
                if error.code != 429 or attempt == 4:
                    raise RuntimeError(f"HTTP {error.code}") from error
                try:
                    delay = float(error.headers.get("retry-after") or 2)
                except ValueError:
                    delay = 2
            time.sleep(delay)


def classify(
    data, timeline, entities, hits, run_id, settings, *, max_comments=None
) -> tuple[list[Finding], list[dict], str | None]:
    key = secrets.get("TYPESAFE_API_KEY")
    if not key:
        return [], [], "jev: TYPESAFE_API_KEY is not set"
    targets = {
        e.id: f"{e.name} ({', '.join(e.aliases)})" if e.aliases else e.name for e in entities
    }
    questions = {
        "category": {
            "type": "choice",
            "instructions": (
                "Classify how the Vietnamese YouTube speech or comment treats the target. "
                "Use surrounding speech or the parent comment as context. "
                "The Party, State or regime may be attacked without being named."
            ),
            "criteria": {
                **VIOLATIONS,
                "legitimate_criticism": (
                    "reasoned criticism of actions, decisions or policies without personal attacks"
                ),
                "neutral": "no violation or unrelated to the target",
            },
        },
        "target": {
            "type": "choice",
            "instructions": "Which listed entity is targeted, explicitly or implicitly?",
            "criteria": {**targets, "none": "does not target any listed entity"},
        },
        "severity": {
            "type": "score",
            "instructions": "How severe is the violation in the speech or comment?",
            "criteria": ["none or low", "medium", "high"],
        },
    }
    shared = {
        "video_title": data.video.title if data.video else "",
        "entities": [{"id": e.id, "name": e.name, "aliases": e.aliases} for e in entities],
    }
    items = []
    segments = timeline.segments
    for i, segment in enumerate(segments):
        if segment.speech.strip():
            items.append(
                (
                    segment.id,
                    segment,
                    {
                        "speech_before": segments[i - 1].speech if i else "",
                        "speech": segment.speech,
                        "speech_after": segments[i + 1].speech if i + 1 < len(segments) else "",
                    },
                )
            )
    texts = {c.id: c.text for c in data.comments}
    for comment in data.comments[:max_comments]:
        items.append(
            (
                comment.id,
                None,
                {"parent_comment": texts.get(comment.parent_id), "comment": comment.text},
            )
        )
    segment_hits = {}
    for hit in hits:
        if hit.segment_id:
            segment_hits.setdefault(hit.segment_id, []).append(hit)

    def request(item):
        item_id, segment, content = item
        record = {
            "task": "jev",
            "item_id": item_id,
            "answers": {},
            "provider": "typesafe",
            "model": MODEL,
            "kept": False,
        }
        try:
            reply = _call(key, {**shared, **content}, questions)
            answers = record["answers"] = reply["answers"]
            record["model"] = reply["model"]
            target = answers["target"]["choice"]
            probs = answers["category"]["probabilities"]
            if target == "none" or sum(probs.get(c, 0.0) for c in VIOLATIONS) < 0.5:
                return None, record
            if target not in targets:
                raise ValueError("Unknown Jev target")
            category = max(VIOLATIONS, key=lambda c: probs.get(c, 0.0))
            p = probs[category]
            score = answers["severity"]["score"]
            location = (
                dict(
                    source_kind="speech",
                    segment_id=item_id,
                    start=segment.start,
                    end=segment.end,
                    triggers=[
                        Trigger(**h.model_dump(exclude={"entity"}))
                        for h in segment_hits.get(item_id, [])
                    ],
                    quote=segment.speech,
                )
                if segment is not None
                else dict(
                    source_kind="comment",
                    comment_id=item_id,
                    quote=content["comment"],
                    triggers=[Trigger(via="comment", comment_id=item_id)],
                )
            )
            finding = Finding(
                id=f"f_{new_ulid()}",
                run_id=run_id,
                video_id=timeline.video_id,
                capture=timeline.capture,
                analyzer="llm",
                analyzer_version="0.1.0",
                model=ModelRef(provider="typesafe", model=record["model"]),
                entity=target,
                category=category,
                reason=f"Jev: {category} p={p:.2f}",
                severity="low" if score < 0.5 else "medium" if score < 1.5 else "high",
                confidence="highly_likely" if p >= 0.85 else "likely" if p >= 0.6 else "unverified",
                **location,
            )
            record["kept"] = True
            return finding, record
        except (OSError, RuntimeError, ValueError, TypeError, KeyError) as error:
            record["error"] = str(error)
            return None, record

    findings, records = [], []
    with ThreadPoolExecutor(max_workers=settings.concurrency) as pool:
        for finding, record in pool.map(request, items):
            if finding is not None:
                findings.append(finding)
            records.append(record)
    errors = [r["error"] for r in records if "error" in r]
    return (
        findings,
        records,
        f"jev: {len(errors)}/{len(records)} requests failed: {errors[0]}" if errors else None,
    )
