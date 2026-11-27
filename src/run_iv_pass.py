"""Run the IV second pass (suva/iv_pass.py) on every invalidity ruling in a DB.

Stores results in table iv_assessments(slug, score, principle, reason_de, model, created_at), next to
the shared schema (no change to the tables the UI reads).

    python src/run_iv_pass.py data/eval_window.sqlite --before 2025-10-01 [--workers 6]

--before: only Suva IV summaries decided before this date are used as illustrations (no label leakage
when evaluating on a later window).
"""
import argparse
import csv
import glob
import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import examples, iv_pass, llm, triage  # noqa: E402


def example_dates():
    dates = {r["case"]: r["decision_date"] for r in csv.DictReader(open(os.path.join(ROOT, "data/bger/index.csv")))}
    for f in glob.glob(os.path.join(ROOT, "data/bger/*.json")):
        meta = json.load(open(f))
        for num in meta.get("Num") or []:
            dates.setdefault(num, meta.get("Datum"))
    return dates


def illustrations(before):
    dates = example_dates()
    out = []
    for ex in examples.load_examples():
        d = dates.get(ex["docket"]) or ""
        f = os.path.join(ROOT, "data/bger", ex["docket"].replace("/", "_") + ".html")
        if not d or d >= before or not os.path.exists(f):
            continue
        import re
        text = re.sub("<[^>]+>", " ", open(f, encoding="utf-8", errors="ignore").read())
        if "invalidity" in triage.classify({"text": text})["areas"]:
            out.append(ex)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--before", required=True, help="only use Suva IV examples decided before this date")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    ill = illustrations(a.before)
    print(f"{len(ill)} illustrations: {', '.join(e['docket'] for e in ill)}")
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS iv_assessments (slug TEXT PRIMARY KEY, score INTEGER, principle TEXT,
                   reason_de TEXT, model TEXT, created_at TEXT)""")
    done = {r[0] for r in con.execute("SELECT slug FROM iv_assessments")}
    rows = [dict(r) for r in con.execute("SELECT slug, docket, decision_date, subject, text FROM judgements")]
    todo = [r for r in rows if r["slug"] not in done
            and "invalidity" in triage.classify({"subject": r["subject"], "text": r["text"]})["areas"]]
    print(f"{len(todo)} invalidity rulings to assess")
    con.commit()

    def work(r):
        # never show the model Suva's own summary of this ruling as an illustration (leakage on the examples set)
        return r, iv_pass.assess_iv(r, [e for e in ill if e["docket"] != r["docket"]])

    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(work, r) for r in todo]
        for f in as_completed(futs):
            try:
                r, res = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr)
                continue
            con.execute("INSERT OR REPLACE INTO iv_assessments VALUES (?,?,?,?,?,?)",
                        (r["slug"], res["score"], res.get("principle", ""), res.get("reason_de", ""),
                         llm.model_name(), datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
            print(f"{r['docket']}: iv={res['score']}", flush=True)


if __name__ == "__main__":
    main()
