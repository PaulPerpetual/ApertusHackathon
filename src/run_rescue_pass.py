"""Run the ATSG rescue pass (suva/rescue_pass.py) on subject-area candidates NOT selected by Apertus v1.

Table rescue_assessments(slug, rescue, verdict, quote_ok, norm, quote, reason, model, created_at).

    python src/run_rescue_pass.py data/eval_window.sqlite [--workers 5]
"""
import argparse
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import llm, rescue_pass, triage  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS rescue_assessments (slug TEXT PRIMARY KEY, rescue INTEGER, verdict INTEGER,
                   quote_ok INTEGER, norm TEXT, quote TEXT, reason TEXT, model TEXT, created_at TEXT)""")
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    con.commit()
    done = {r[0] for r in con.execute("SELECT slug FROM rescue_assessments")}
    iv = "i.score" if "iv_assessments" in tables else "NULL"
    rows = [dict(r) for r in con.execute(f"""SELECT j.slug, j.docket, j.subject, j.text,
            {'COALESCE(f.main_score, a.ai_score)' if 'final_selection' in tables else 'a.ai_score'} AS main, {iv} AS iv
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            {'LEFT JOIN iv_assessments i ON i.slug = j.slug' if 'iv_assessments' in tables else ''}
            {'LEFT JOIN final_selection f ON f.slug = j.slug' if 'final_selection' in tables else ''}""")]
    todo = []
    for r in rows:
        c = triage.classify({"subject": r["subject"], "text": r["text"]})
        selected = (r["main"] or 0) >= 60 or ("invalidity" in c["areas"] and (r["iv"] or 0) >= 40)
        if c["areas"] and not selected and r["slug"] not in done:
            todo.append(r)
    print(f"{len(todo)} rejected candidates to re-check", flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(lambda r: (r, rescue_pass.assess(r)), r) for r in todo]
        for f in as_completed(futs):
            try:
                r, x = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            con.execute("INSERT OR REPLACE INTO rescue_assessments VALUES (?,?,?,?,?,?,?,?,?)",
                        (r["slug"], int(x["rescue"]), int(x["verdict"]), int(x["quote_ok"]), x["norm"], x["quote"],
                         x["reason"], llm.model_name(), datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
            print(f"{r['docket']}: rescue={x['rescue']} (said {x['verdict']}, quote ok {x['quote_ok']}) {x['norm']}", flush=True)


if __name__ == "__main__":
    main()
