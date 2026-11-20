"""T24: phân tích comment bằng LLM, dùng provider giả."""

import json

import pytest

from h4wk.ai.base import ProviderReply, ProviderRequest
from h4wk.ai.config import AI_CONFIG_PATH
from h4wk.ai.gateway import AIGateway
from h4wk.analysis import comments, runner
from h4wk.analysis.models import Category
from h4wk.analysis.static import LexiconEntry
from h4wk.collectors.models import Comment, Normalized, Video
from h4wk.core.config_models import CommentSettings
from h4wk.core.entities import Entity
from h4wk.media.timeline import Timeline

ENTITY = Entity(id="e_01", name="Trần Văn Mẫu")
INSULT = [LexiconEntry("đồ hèn", "insult", Category.INSULT)]


class Judge:
    """Trả lời theo nội dung yêu cầu: comment nào được chỉ định thì vi phạm, còn lại neutral."""

    def __init__(self, violating=(), extra=(), fail_comments=False):
        self.violating = set(violating)
        self.extra = list(extra)
        self.fail_comments = fail_comments
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderReply:
        self.requests.append(request)
        body = json.loads(request.messages[1]["content"])
        if "comments" not in body:
            return ProviderReply('{"verdicts":[]}')
        verdicts = [
            {
                "comment_id": c["id"],
                "entity": "e_01",
                "category": "insult" if c["id"] in self.violating else "neutral",
                "severity": "medium",
                "confidence": "likely",
                "quote": c["text"],
                "reason": "Lý do.",
            }
            for c in body["comments"]
        ]
        return ProviderReply(json.dumps({"verdicts": verdicts + self.extra}))

    @property
    def comment_bodies(self) -> list[dict]:
        bodies = [json.loads(r.messages[1]["content"]) for r in self.requests]
        return [b for b in bodies if "comments" in b]


def _gateway(provider, tmp_path, config_path=None):
    return AIGateway(
        {"anthropic": provider},
        config_path=config_path or AI_CONFIG_PATH.with_suffix(".toml.example"),
        log_dir=tmp_path,
    )


def _data(n=500, mentions=95, replies=()):
    items = [
        Comment(id=f"c{i}", text="Trần Văn Mẫu đồ hèn" if i < mentions else f"bình luận {i}")
        for i in range(n)
    ]
    items += [Comment(id=cid, parent_id=parent, text=text) for cid, parent, text in replies]
    video = Video(id="v", channel_id="UCx", title="T", description="D")
    data = Normalized(schema="h4wk.normalized/1", video=video, comments=items)
    timeline = Timeline(schema="h4wk.timeline/1", video_id="v", capture="20261118T160000")
    return data, timeline


def _run(tmp_path, provider, data, timeline, lexicon=(), settings=None, entities=(ENTITY,)):
    return runner.analyze(
        data,
        timeline,
        list(entities),
        list(lexicon),
        "r_x",
        tmp_path / "out",
        gateway=_gateway(provider, tmp_path),
        comment_settings=settings,
    )


def _calls(tmp_path):
    rows = (tmp_path / "ai_calls.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(r)["task"] for r in rows]


def test_500_comments_95_hits_use_four_requests(tmp_path):
    data, timeline = _data()
    provider = Judge()
    _, findings, error = _run(tmp_path, provider, data, timeline)
    assert error is None and findings == []
    assert len(provider.comment_bodies) == 4 == -(-95 // 30)
    assert _calls(tmp_path).count("analysis.classify_comment") == 4
    assert sum(len(b["comments"]) for b in provider.comment_bodies) == 95


def test_finding_points_to_comment(tmp_path):
    data, timeline = _data(n=50, mentions=10)
    provider = Judge(violating={"c3"})
    _, findings, _ = _run(tmp_path, provider, data, timeline)
    assert len(findings) == 1
    f = findings[0]
    assert f.analyzer == "llm" and f.source_kind == "comment" and f.model.provider == "anthropic"
    assert f.comment_id == "c3" and f.quote == "Trần Văn Mẫu đồ hèn"
    assert f.triggers[0].comment_id == "c3" and f.triggers[0].via == "comment"
    records = json.loads((tmp_path / "out" / "llm.json").read_text(encoding="utf-8"))
    assert {r["task"] for r in records} == {"analysis.classify_comment"}
    assert {r["item_id"]: r["kept"] for r in records}["c3"] is True


def test_max_per_video_limits_comments_sent(tmp_path):
    data, timeline = _data(n=100, mentions=60)
    provider = Judge()
    _run(tmp_path, provider, data, timeline, settings=CommentSettings(max_per_video=25))
    assert [len(b["comments"]) for b in provider.comment_bodies] == [25]


def test_reply_carries_parent_text(tmp_path):
    data, timeline = _data(n=3, mentions=1, replies=[("r1", "c0", "Mẫu đồ hèn thật")])
    data.comments[-1] = data.comments[-1].model_copy(update={"text": "Trần Văn Mẫu thật"})
    provider = Judge()
    _run(tmp_path, provider, data, timeline)
    sent = {c["id"]: c for b in provider.comment_bodies for c in b["comments"]}
    assert sent["r1"]["parent_text"] == "Trần Văn Mẫu đồ hèn"
    assert sent["c0"]["parent_text"] is None


def test_invalid_verdicts_are_not_findings(tmp_path):
    data, timeline = _data(n=5, mentions=2)
    extra = [
        {
            "comment_id": "c99",
            "entity": "e_01",
            "category": "insult",
            "severity": "low",
            "confidence": "likely",
            "quote": "x",
            "reason": "r",
        },
        {
            "comment_id": "c0",
            "entity": "e_99",
            "category": "insult",
            "severity": "low",
            "confidence": "likely",
            "quote": "x",
            "reason": "r",
        },
    ]
    provider = Judge(extra=extra)
    _, findings, _ = _run(tmp_path, provider, data, timeline)
    assert findings == []
    records = json.loads((tmp_path / "out" / "llm.json").read_text(encoding="utf-8"))
    assert [r["kept"] for r in records] == [False] * 4
    assert sum("error" in r for r in records) == 2


def test_llm_replaces_static_only_for_same_comment(tmp_path):
    data, timeline = _data(n=5, mentions=2)  # c0 và c1 đều bị tầng tĩnh bắt
    provider = Judge(violating={"c0"})
    _, findings, _ = _run(tmp_path, provider, data, timeline, lexicon=INSULT)
    kinds = {(f.comment_id, f.analyzer) for f in findings}
    assert kinds == {("c0", "llm"), ("c1", "static")}


def test_comment_failure_keeps_segment_part(tmp_path):
    from h4wk.media.timeline import Segment

    data, timeline = _data(n=3, mentions=2)
    timeline = timeline.model_copy(
        update={"segments": [Segment(id="seg_0001", start=0, end=5, speech="Trần Văn Mẫu")]}
    )

    class Flaky(Judge):
        def complete(self, request):
            body = json.loads(request.messages[1]["content"])
            if "comments" in body:
                return ProviderReply("không phải JSON")
            self.requests.append(request)
            item = body["items"][0]["id"]
            verdict = {
                "item_id": item,
                "entity": "e_01",
                "source_kind": "speech",
                "category": "insult",
                "severity": "low",
                "confidence": "likely",
                "quote": "q",
                "reason": "r",
            }
            return ProviderReply(json.dumps({"verdicts": [verdict]}))

    _, findings, error = _run(tmp_path, Flaky(), data, timeline)
    assert [f.source_kind for f in findings if f.analyzer == "llm"] == ["speech"]
    assert error and "analysis.classify_comment" in error


@pytest.mark.parametrize("mentions", [0])
def test_no_comment_hits_means_no_comment_request(tmp_path, mentions):
    data, timeline = _data(n=10, mentions=mentions)
    provider = Judge()
    _, _, error = _run(tmp_path, provider, data, timeline)
    assert error is None and provider.requests == []
    assert comments.select_comments(data, [], CommentSettings()) == []
