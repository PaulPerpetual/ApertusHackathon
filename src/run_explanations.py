"""Rewrite triage explanations specifically (suva/explain.py) for every Apertus-scored ruling.

Stores them in table explanations(slug, de, fr, model, created_at); finalize.py uses them for the cards.

    python src/run_explanations.py data/aprjun.sqlite [--workers 3] [--redo] [--only 8C_17/2026]
"""
import argparse
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import explain, llm  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS explanations (slug TEXT PRIMARY KEY, de TEXT, fr TEXT, model TEXT, created_at TEXT)")
    con.commit()
    done = set() if a.redo else {r[0] for r in con.execute("SELECT slug FROM explanations")}
    has_fin = con.execute("SELECT 1 FROM sqlite_master WHERE name='final_selection'").fetchone()
    score = "COALESCE(f.main_score, a.ai_score)" if has_fin else "a.ai_score"
    rows = [dict(r) for r in con.execute(f"""SELECT j.slug, j.docket, j.subject, j.text, {score} AS score FROM judgements j
            JOIN assessments a ON a.slug = j.slug {'LEFT JOIN final_selection f ON f.slug = j.slug' if has_fin else ''}
            WHERE a.model LIKE 'apertus%'""")]
    todo = [r for r in rows if r["slug"] not in done and (not a.only or r["docket"] == a.only)]
    print(f"{len(todo)} explanations to write", flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(lambda r: (r, explain.explain(r, r["score"])), r) for r in todo]
        for f in as_completed(futs):
            try:
                r, x = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            con.execute("INSERT OR REPLACE INTO explanations VALUES (?,?,?,?,?)",
                        (r["slug"], x["de"], x["fr"], llm.model_name(), datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
            print(f"{r['docket']}: {x['de'][:110]}", flush=True)


if __name__ == "__main__":
    main()
