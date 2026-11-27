"""Run pass 5 (suva/rank_pass.py) on hit-list rulings: v1-selected, or Tier 1/2 (assessments.tier) when present.

Table rankings(slug, importance, reason, model, created_at).

    python src/run_rank_pass.py data/eval_window.sqlite [--workers 6] [--all-candidates]
"""
import argparse
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import llm, rank_pass, triage  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--all-candidates", action="store_true", help="rank every subject-area candidate, not only the hit list")
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS rankings (slug TEXT PRIMARY KEY, importance INTEGER, reason TEXT, model TEXT, created_at TEXT)")
    con.commit()
    t = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    acols = {r[1] for r in con.execute("PRAGMA table_info(assessments)")}
    rows = [dict(r) for r in con.execute(f"""SELECT j.slug, j.docket, j.subject, j.text, a.explanation_de,
            {'COALESCE(f.main_score, a.ai_score)' if 'final_selection' in t else 'a.ai_score'} AS main,
            {'i.score' if 'iv_assessments' in t else 'NULL'} AS iv, {'a.tier' if 'tier' in acols else 'NULL'} AS tier
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            {'LEFT JOIN final_selection f ON f.slug = j.slug' if 'final_selection' in t else ''}
            {'LEFT JOIN iv_assessments i ON i.slug = j.slug' if 'iv_assessments' in t else ''}""")]
    done = {r[0] for r in con.execute("SELECT slug FROM rankings")}
    todo = []
    for r in rows:
        c = triage.classify({"subject": r["subject"], "text": r["text"]})
        on_list = r["tier"] in (1, 2) if r["tier"] is not None else ((r["main"] or 0) >= 60 or ("invalidity" in c["areas"] and (r["iv"] or 0) >= 40))
        if r["slug"] not in done and c["areas"] and (on_list or a.all_candidates):
            todo.append(r)
    print(f"{len(todo)} rulings to rank", flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(lambda r: (r, rank_pass.assess(r, r["explanation_de"] or "")), r) for r in todo]
        for f in as_completed(futs):
            try:
                r, x = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            con.execute("INSERT OR REPLACE INTO rankings VALUES (?,?,?,?,?)",
                        (r["slug"], x["importance"], x["reason"], llm.model_name(), datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
            print(f"{r['docket']}: {x['importance']}", flush=True)


if __name__ == "__main__":
    main()
