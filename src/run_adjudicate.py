"""Run pass 4 (suva/adjudicate.py) on every subject-area candidate in a DB.

Table adjudications(slug, tier, reason, model, created_at).

    python src/run_adjudicate.py data/eval_window.sqlite [--workers 6]
"""
import argparse
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import adjudicate, llm, triage  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS adjudications (slug TEXT PRIMARY KEY, tier INTEGER, reason TEXT, model TEXT, created_at TEXT)")
    con.commit()
    t = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    q = f"""SELECT j.slug, j.docket, j.subject, j.text,
                   {'COALESCE(f.main_score, a.ai_score)' if 'final_selection' in t else 'a.ai_score'} AS main,
                   a.explanation_de AS explanation,
                   {'i.score' if 'iv_assessments' in t else 'NULL'} AS iv, {'i.principle' if 'iv_assessments' in t else 'NULL'} AS iv_principle,
                   {'r.verdict' if 'rescue_assessments' in t else 'NULL'} AS rescue_verdict,
                   {'r.norm' if 'rescue_assessments' in t else 'NULL'} AS rescue_norm,
                   {'r.quote' if 'rescue_assessments' in t else 'NULL'} AS rescue_quote,
                   {'r.reason' if 'rescue_assessments' in t else 'NULL'} AS rescue_reason
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            {'LEFT JOIN final_selection f ON f.slug = j.slug' if 'final_selection' in t else ''}
            {'LEFT JOIN iv_assessments i ON i.slug = j.slug' if 'iv_assessments' in t else ''}
            {'LEFT JOIN rescue_assessments r ON r.slug = j.slug' if 'rescue_assessments' in t else ''}"""
    done = {r[0] for r in con.execute("SELECT slug FROM adjudications")}
    rows = [dict(r) for r in con.execute(q)]
    todo = [r for r in rows if r["slug"] not in done and triage.classify({"subject": r["subject"], "text": r["text"]})["areas"]]
    print(f"{len(todo)} candidates to adjudicate", flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(lambda r: (r, adjudicate.assess(r, adjudicate.evidence_text(r))), r) for r in todo]
        for f in as_completed(futs):
            try:
                r, x = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            con.execute("INSERT OR REPLACE INTO adjudications VALUES (?,?,?,?,?)",
                        (r["slug"], x["tier"], x["reason"], llm.model_name(), datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
            print(f"{r['docket']}: tier {x['tier']}", flush=True)


if __name__ == "__main__":
    main()
