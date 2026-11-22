
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from h4wk.analysis import jev
from h4wk.core import secrets

src, out = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, encoding="utf-8")))
key = secrets.get("TYPESAFE_API_KEY")
shared, questions = jev._configuration([], "")


def ask(row):
    state = {**shared, "source_type": "YouTube comment", "text": row["text"]}
    try:
        reply = jev._call(key, state, questions)
        return {**row, "answers": reply["answers"], "usage": reply.get("usage")}
    except Exception as e:
        return {**row, "error": str(e)}


with ThreadPoolExecutor(4) as pool, open(out, "w", encoding="utf-8") as f:
    for r in pool.map(ask, rows):
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("done", len(rows))
