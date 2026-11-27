"""Write Apertus DE/FR summaries for every selected ruling (final_selection.selected = 1).

Order: newest month first (June 2026 feeds Suva's quality score), then by score.
Skips rulings that already have both summaries. Never shows the model Suva's own summary of the
same ruling (pipeline rule).

    python src/run_summaries.py data/aprjun.sqlite [--workers 4] [--limit N] [--month 2026-06]
"""
import argparse
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--month", default="", help="only rulings decided in this month, e.g. 2026-06")
    a = ap.parse_args()
    os.environ["SUVA_DB"] = os.path.abspath(a.db)  # before importing suva.config
    from suva import db, examples, llm, summarize

    exs = examples.load_examples()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("""
        SELECT j.*, a.ai_score FROM judgements j JOIN assessments a ON a.slug = j.slug
        JOIN final_selection f ON f.slug = j.slug
        WHERE f.selected = 1 AND (SELECT COUNT(*) FROM summaries s WHERE s.slug = j.slug) < 2
        ORDER BY substr(j.decision_date, 1, 7) DESC, a.ai_score DESC, j.decision_date DESC""")]
    con.close()
    if a.month:
        rows = [r for r in rows if (r["decision_date"] or "").startswith(a.month)]
    if a.limit:
        rows = rows[:a.limit]
    print(f"{len(rows)} rulings to summarise", flush=True)

    def work(j):
        shots = [e for e in exs if e["docket"] != j["docket"]]  # never leak Suva's own summary
        return j, summarize.summarize(j, shots)

    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(work, j) for j in rows]
        for f in as_completed(futs):
            try:
                j, s = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            with db.connect() as c:
                for lang in ("de", "fr"):
                    db.save_summary(c, j["slug"], lang, s[lang], llm.model_name())
            print(f"{j['docket']} ({j['decision_date']}): de {len(s['de'].split())} w, fr {len(s['fr'].split())} w",
                  flush=True)


if __name__ == "__main__":
    main()
