"""Phân loại lời nói và bình luận qua Jev."""

import base64
import json
import math
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2

from h4wk.analysis import jev_log
from h4wk.analysis.models import Finding, ModelRef, Trigger
from h4wk.core import secrets
from h4wk.core.ids import new_ulid

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
MAX_IMAGES = 4
CONCURRENCY = 4
QUESTIONS = {
    "category": {
        "type": "choice",
        "instructions": (
            "`text` is a Vietnamese YouTube item (see `source_type`). Decide whether `text` "
            "itself attacks any of the `protected_targets`. An insult or accusation aimed at "
            "anyone else (foreign leaders, historical figures, other commenters, the channel) is "
            "neutral. A"
            " comment that only replies to `parent_comment` is judged by what the reply itself "
            "says: agreeing with an attack counts, but a question, joke or remark about another"
            " topic does not. Reporting facts, describing what leaders did, analysis and "
            "predictions in news, titles, descriptions or narration are legitimate_criticism or"
            " neutral unless they use insults, mockery, or accuse the protected targets of "
            "crimes, corruption or betrayal without proof. Boilerplate such as links, donation "
            "appeals and hashtags is neutral."
        ),
        "criteria": {
            "insult": {
                "what": (
                    "insults, slanders, curses, mocks or humiliates a protected target, "
                    "including sarcasm and derogatory nicknames"
                ),
                "examples": [
                    "Thằng này ngu như bò",
                    "Bọn cộng sản là lũ cướp",
                    "Ngài tổng bí thư vĩ đại quá nhỉ, cười chết mất",
                ],
            },
            "unsupported_accusation": {
                "what": (
                    "accuses a protected target of a crime, corruption or betrayal without "
                    "presenting evidence"
                ),
                "examples": ["Ông ta bán nước cho Tàu", "Cả bộ máy này ăn hối lộ hết"],
            },
            "fabrication": {
                "what": "distorts facts or spreads made-up information about a protected target",
                "examples": [
                    "Nghe nói ông ấy đã bỏ trốn ra nước ngoài",
                    "Đảng đã tự tay giết hàng triệu dân",
                ],
            },
            "incitement": {
                "what": (
                    "calls for hatred, violence, overthrow or division against a protected target"
                ),
                "examples": ["Đứng lên lật đổ chế độ này đi", "Phải treo cổ bọn lãnh đạo"],
            },
            "state_secret": {
                "what": "reveals state secrets",
                "examples": ["Đây là tài liệu mật của Bộ Chính trị, tôi tung lên đây"],
            },
            "legitimate_criticism": {
                "what": (
                    "criticizes, doubts or analyzes a policy, decision or the system of a "
                    "protected target, or predicts its failure, without insults, mockery or "
                    "unproven accusations of crimes"
                ),
                "examples": [
                    "Chính sách sáp nhập tỉnh làm người dân mất giấy tờ, thủ tục rườm rà hơn",
                    (
                        "Tôi lo kế hoạch tăng trưởng hai con số khó thực hiện vì bất động sản "
                        "đang đóng băng"
                    ),
                    "Chế độ độc đảng nào rồi cũng phải thay đổi nếu không theo kịp thời đại",
                    "Vì sao luật mới có thể gây bất ổn cho chính quyền?",
                ],
            },
            "neutral": {
                "what": (
                    "does not attack the protected targets: praise, neutral remarks, questions,"
                    " news reporting, boilerplate links or hashtags, or insults aimed at "
                    "someone else"
                ),
                "examples": [
                    "Ông Tô Lâm gặp Tổng thống Putin hôm qua",
                    "Ủng hộ ông Tô Lâm",
                    "Ông Putin là kẻ xâm lược",
                    "Video hay quá, cảm ơn kênh",
                    "Đúng vậy",
                    "Đăng ký kênh để xem thêm: https://youtube.com/...",
                ],
            },
        },
    },
    "severity": {
        "type": "score",
        "instructions": "How severe is the violation in the speech or comment?",
        "criteria": ["none or low", "medium", "high"],
    },
    "is_attack": {
        "type": "noul",
        "instructions": (
            "Does `text` itself personally attack, slander, curse, mock, or accuse without "
            "evidence any of the `protected_targets`? Say no for praise, news, questions, "
            "predictions, historical analysis and reasoned criticism of policy."
        ),
    },
    "target": {
        "type": "choice",
        "instructions": (
            "Which listed entity does `text` target, explicitly or implicitly? Pick `none` when"
            " `text` is not directed at any protected target."
        ),
        "criteria": {
            "none": (
                "does not target any protected entity: praise, news, other people, other "
                "countries or off-topic"
            )
        },
    },
}
QUESTIONS["violation"] = {
    "type": "choice",
    "instructions": (
        "`text` is a Vietnamese YouTube item (see `source_type`). Regardless of who is targeted,"
        " does `text` itself do one of the harmful acts below? Judge what the text does, not the"
        " opinions it holds: news reporting about such acts, criticism, satire without a call to"
        " act, history and political opinions are `none`. Insults, curses, wishing bad karma,"
        " crude jokes and metaphors aimed at officials, monks, commenters or other individuals"
        " are `none` unless they call for real physical harm. Prejudice about regions or"
        " political sides is `none`."
    ),
    "criteria": {
        "violence": {
            "what": (
                "a real call, plan or instruction for physical violence, armed attacks, riots, "
                "terrorism or sabotage of infrastructure, or praise of a real attack; not "
                "figures of speech"
            ),
            "examples": [
                "Mọi người mang dao gậy ra đường tối nay, gặp công an là đánh",
                "Hướng dẫn chế bom xăng để đốt trụ sở",
                "Vụ đánh bom hôm qua là anh hùng, cần làm thêm nhiều vụ nữa",
            ],
        },
        "hate": {
            "what": (
                "dehumanizes, or calls for harm, expulsion or discrimination against, a whole "
                "ethnic group, religion or nationality"
            ),
            "examples": [
                "Bọn người dân tộc đó toàn lũ ăn bám, phải đuổi hết về rừng",
                "Đạo đó là tà giáo, gặp tín đồ của nó thì cứ đánh",
            ],
        },
        "state_secret": {
            "what": "publishes classified state or work secrets",
            "examples": ["Đây là văn bản mật của Bộ Quốc phòng, tôi đăng toàn bộ cho mọi người"],
        },
        "forgery": {
            "what": (
                "presents a forged website, seal, document or ID of a state agency as real, or a"
                " fake AI-made video, image or voice of a real official presented as real"
            ),
            "examples": [
                "Quyết định có đóng dấu này do tôi tự làm nhưng cứ đăng như văn bản thật",
                "Clip giọng ông bộ trưởng tuyên bố đổi tiền, làm bằng AI nhưng đừng nói ra",
            ],
        },
        "none": {
            "what": (
                "none of the above: opinions, criticism, news, history, jokes, or reporting "
                "on such acts without supporting them"
            ),
            "examples": [
                "Hôm qua có bạo loạn ở thành phố X, cảnh sát đã giải tán",
                "Tôi phản đối chính sách này",
                "Video hay quá",
            ],
        },
    },
}
VIOLATIONS = ("insult", "unsupported_accusation", "fabrication", "incitement", "state_secret")
CONTENT_VIOLATIONS = ("violence", "hate", "state_secret", "forgery")


def _configuration(entities, video_title):
    """Câu hỏi gửi Jev. Không có đối tượng thì chỉ hỏi vi phạm theo nội dung và mức độ."""
    targets = {
        e.id: ", ".join(
            [e.name, *e.aliases, *e.abbreviations, *([e.description] if e.description else [])]
        )
        for e in entities
    }
    if not targets:
        questions = {k: QUESTIONS[k] for k in ("violation", "severity")}
        return {"video_title": video_title}, questions
    questions = {
        **QUESTIONS,
        "target": {
            **QUESTIONS["target"],
            "criteria": {**targets, **QUESTIONS["target"]["criteria"]},
        },
    }
    return {"protected_targets": "; ".join(targets.values()), "video_title": video_title}, questions


def _keep(answers):
    if "target" not in answers:
        return False
    return answers["is_attack"]["noul"] >= 0.5 and answers["target"]["choice"] != "none"


CONTENT_THRESHOLD = 0.6


def _content_violation(answers):
    """(danh mục, xác suất có vi phạm) hoặc None. Xét tổng xác suất các danh mục để câu vừa
    bạo lực vừa thù hận (xác suất chia đôi) không bị bỏ sót; danh mục là cái cao nhất."""
    probs = answers.get("violation", {}).get("probabilities", {})
    total = sum(probs.get(c, 0.0) for c in CONTENT_VIOLATIONS)
    if total < CONTENT_THRESHOLD:
        return None
    return max(CONTENT_VIOLATIONS, key=lambda c: probs.get(c, 0.0)), min(total, 1.0)


def _encode(path: Path) -> str:
    """JPEG base64 cạnh dài tối đa 1024, cạnh ngắn ít nhất 320 (Jev từ chối ảnh quá nhỏ)."""
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Cannot read image {path.name}")
    h, w = image.shape[:2]
    scale = max(min(1024 / max(w, h), 1), 320 / min(w, h))
    if scale != 1:
        image = cv2.resize(image, (round(w * scale), round(h * scale)))
    ok, data = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError(f"Cannot encode image {path.name}")
    return base64.b64encode(data.tobytes()).decode("ascii")


def _call(key, state, questions, images=()):
    body = {"model": MODEL, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if images:
        headers["TypeSafe-Danger-Zone-Images"] = "true"
        assets = {
            f"<image-{i}>": {"type": "image", "format": "jpeg", "data_base64": _encode(path)}
            for i, path in enumerate(images, 1)
        }
        body.update(assets=assets, state=[*assets, state])
    request = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), headers=headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            with error:
                if error.code != 429 or attempt == 4:
                    raise RuntimeError(f"HTTP {error.code}") from error
                jev_log.count_retry()
                try:
                    delay = float(error.headers.get("retry-after") or 2)
                except ValueError:
                    delay = 2
            time.sleep(delay)


def _validate_reply(reply) -> None:
    if (
        not isinstance(reply, dict)
        or not isinstance(reply.get("model"), str)
        or not reply["model"].strip()
        or not isinstance(reply.get("answers"), dict)
    ):
        raise ValueError("Invalid Jev response")


def test_connection() -> dict:
    """Một câu hỏi `noul` ngắn để thử key; ghi thống kê nhưng không trả nội dung."""
    key = secrets.get("TYPESAFE_API_KEY")
    if not key:
        return {"ok": False, "error": "TYPESAFE_API_KEY is not set"}
    questions = {"is_attack": {"type": "noul", "instructions": "Is this text an attack?"}}
    started = time.perf_counter()
    jev_log.take_retries()
    reply = None
    status = "ok"
    try:
        reply = _call(key, {"text": "Xin chào"}, questions)
        _validate_reply(reply)
        score = reply["answers"]["is_attack"]["noul"]
        if type(score) not in (int, float) or not 0 <= score <= 1:
            raise ValueError("Invalid Jev answer")
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        status = jev_log.error_status(str(error))
    jev_log.record(
        video_id=None,
        capture=None,
        run_id=None,
        source_kind="connection_test",
        images=0,
        reply=reply if isinstance(reply, dict) else None,
        kept=False,
        status=status,
        retries_429=jev_log.take_retries(),
    )
    if status != "ok":
        return {"ok": False, "error": status}
    return {
        "ok": True,
        "model": reply.get("model"),
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


def _location(kind, item_id, text, hits, target, *, segment=None, frame=None):
    location = dict(source_kind=kind, quote=text, triggers=[])
    if kind == "comment":
        location.update(comment_id=item_id, triggers=[Trigger(via="comment", comment_id=item_id)])
    if segment is not None:
        location.update(segment_id=segment.id, start=segment.start, end=segment.end)
    if frame is not None:
        location["frame"] = frame
    if kind != "comment":
        location["triggers"] = [
            Trigger(**hit.model_dump(exclude={"entity"}))
            for hit in hits
            if hit.entity == target
            and hit.segment_id == location.get("segment_id")
            and (hit.via == kind or kind == "visual" and hit.via in {"face", "ref_image"})
            and (frame is None or hit.frame == frame)
        ]
    return location


def classify(
    data,
    timeline,
    entities,
    hits,
    run_id,
    *,
    derived_dir: Path | None = None,
    capture_dir: Path | None = None,
) -> tuple[list[Finding], list[dict], str | None]:
    """Keyframe đọc từ `derived_dir`, thumbnail từ `capture_dir`; thiếu thư mục thì chỉ gửi chữ."""
    key = secrets.get("TYPESAFE_API_KEY")
    if not key:
        return [], [], "jev: TYPESAFE_API_KEY is not set"
    shared, questions = _configuration(entities, data.video.title if data.video else "")
    items = []

    def add(kind, item_id, source_type, text, *, segment=None, frame=None, images=(), **context):
        if text.strip() or images:
            items.append(
                (
                    item_id,
                    {"source_type": source_type, "text": text, **context},
                    (kind, segment, frame, images),
                )
            )

    if data.video:
        add("title", "title", "video title", data.video.title)
        add("description", "description", "video description", data.video.description)
    segments = timeline.segments
    seen = set()
    for i, segment in enumerate(segments):
        add(
            "speech",
            segment.id,
            "speech transcript segment",
            segment.speech,
            segment=segment,
            speech_before=segments[i - 1].speech if i else "",
            speech_after=segments[i + 1].speech if i + 1 < len(segments) else "",
        )
        ocr = []
        for row in segment.ocr:
            line = row.text.strip()
            if line and line not in seen:
                seen.add(line)
                ocr.append(row)
        step = max(1, math.ceil(len(segment.frames) / MAX_IMAGES))
        frames = segment.frames[::step] if derived_dir else []
        if ocr or frames:
            kind = "ocr" if ocr else "visual"
            add(
                kind,
                f"{segment.id}:{kind}",
                "video keyframe images; `text` is the text overlaid on them (OCR)",
                " | ".join(row.text.strip() for row in ocr),
                segment=segment,
                frame=ocr[0].frame if ocr else frames[0].frame,
                images=[derived_dir / f.frame for f in frames],
            )
    for thumb in timeline.thumbnails:
        lines = list(dict.fromkeys(row.text.strip() for row in thumb.ocr))
        add(
            "thumbnail",
            thumb.file,
            "video thumbnail image; `text` is the text on it (OCR)",
            " | ".join(line for line in lines if line),
            frame=thumb.file,
            images=[capture_dir / thumb.file] if capture_dir else [],
        )
    texts = {c.id: c.text for c in data.comments}
    for comment in data.comments:
        parent = texts.get(comment.parent_id)
        add(
            "comment",
            comment.id,
            "YouTube comment",
            comment.text,
            **({"parent_comment": parent} if parent else {}),
        )

    def judge(item):
        item_id, content, (kind, segment, frame, images) = item
        record = {
            "task": "jev",
            "item_id": item_id,
            "source_kind": kind,
            "answers": {},
            "provider": "typesafe",
            "model": MODEL,
            "kept": False,
        }
        try:
            reply = _call(key, {**shared, **content}, questions, images)
            _validate_reply(reply)
            record["usage"] = reply.get("usage")
            answers = record["answers"] = reply["answers"]
            record["model"] = reply["model"]
            target = answers.get("target", {}).get("choice")
            probs = answers.get("category", {}).get("probabilities", {})
            by_content = _content_violation(answers)
            if _keep(answers):
                if target not in questions["target"]["criteria"]:
                    raise ValueError("Unknown Jev target")
                category = max(VIOLATIONS, key=lambda c: probs.get(c, 0.0))
                p = probs[category]
            elif by_content is not None:
                target = None
                category, p = by_content
            else:
                return None, record
            score = answers["severity"]["score"]
            finding = Finding(
                id=f"f_{new_ulid()}",
                run_id=run_id,
                video_id=timeline.video_id,
                capture=timeline.capture,
                analyzer="jev",
                analyzer_version="0.1.0",
                model=ModelRef(provider="typesafe", model=record["model"]),
                entity=target,
                category=category,
                reason=f"Jev: {category} p={p:.2f}",
                severity="low" if score < 0.5 else "medium" if score < 1.5 else "high",
                confidence="highly_likely" if p >= 0.85 else "likely" if p >= 0.6 else "unverified",
                **_location(
                    kind, item_id, content["text"], hits, target, segment=segment, frame=frame
                ),
            )
            record["kept"] = True
            return finding, record
        except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError) as error:
            record["error"] = str(error)
            return None, record

    def request(item):
        jev_log.take_retries()
        finding, record = judge(item)
        jev_log.record(
            video_id=timeline.video_id,
            capture=timeline.capture,
            run_id=run_id,
            source_kind=record["source_kind"],
            images=len(item[2][3]),
            reply={"usage": record.get("usage")},
            kept=record["kept"],
            status=jev_log.error_status(record["error"]) if "error" in record else "ok",
            retries_429=jev_log.take_retries(),
        )
        return finding, record

    findings, records = [], []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
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
