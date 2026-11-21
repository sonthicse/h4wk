from pathlib import Path

from h4wk.analysis.models import Category
from h4wk.analysis.static import LexiconEntry
from h4wk.collectors.models import Normalized
from h4wk.core.entities import Entity
from h4wk.media.timeline import Timeline

SAMPLE = Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001"
CAPTURE = "20261118T160000"
ENTITY = Entity(id="e_01", name="Trần Văn Mẫu", aliases=["Mẫu Ca"], abbreviations=["TVM"])
INSULT = [LexiconEntry("đồ hèn", "insult", Category.INSULT)]


def _data() -> tuple[Normalized, Timeline]:
    data = Normalized.model_validate_json(
        (SAMPLE / "captures" / CAPTURE / "normalized.json").read_text(encoding="utf-8")
    )
    timeline = Timeline.model_validate_json(
        (SAMPLE / "derived" / CAPTURE / "timeline.json").read_text(encoding="utf-8")
    )
    return data, timeline
