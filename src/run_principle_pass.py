"""Run the principle pass (suva/principle_pass.py) on invalidity rulings and procedural accident rulings.

Results go to table principle_assessments(slug, score, typ, uvg, rechtsfrage, grundsatz, reason_de, model, created_at).

    python src/run_principle_pass.py data/eval_window.sqlite [--workers 4]
"""
import argparse
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import llm, principle_pass, triage  # noqa: E402


def in_scope(c):
    return "invalidity" in c["areas"] or ("accident" in c["areas"] and c["procedural"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS principle_assessments (slug TEXT PRIMARY KEY, score INTEGER, typ TEXT,
                   uvg INTEGER, rechtsfrage TEXT, grundsatz TEXT, reason_de TEXT, model TEXT, created_at TEXT)""")
    con.commit()
    done = {r[0] for r in con.execute("SELECT slug FROM principle_assessments")}
    rows = [dict(r) for r in con.execute("SELECT slug, docket, decision_date, subject, text FROM judgements")]
    todo = [r for r in rows if r["slug"] not in done
            and in_scope(triage.classify({"subject": r["subject"], "text": r["text"]}))]
    print(f"{len(todo)} rulings in scope", flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(lambda r: (r, principle_pass.assess(r)), r) for r in todo]
        for f in as_completed(futs):
            try:
                r, x = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            con.execute("INSERT OR REPLACE INTO principle_assessments VALUES (?,?,?,?,?,?,?,?,?)",
                        (r["slug"], x["score"], x.get("typ", ""), int(bool(x.get("fuer_uvg_massgebend"))),
                         x.get("rechtsfrage", ""), x.get("grundsatz", ""), x.get("reason_de", ""), llm.model_name(),
                         datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
            print(f"{r['docket']}: p={x['score']} {x.get('typ')} uvg={x.get('fuer_uvg_massgebend')}", flush=True)


if __name__ == "__main__":
    main()
