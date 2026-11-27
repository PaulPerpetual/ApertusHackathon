"""Run the recall pass (suva/recall_pass.py) on borderline subject-area candidates of a triaged DB.

Only rulings the main triage scored in [--low, --high) get LLM calls (--samples each); leading-case signals
are recorded for every candidate. Table recall_assessments(slug, score, scores, leading, reason_de, model,
created_at); the main assessments are not touched. Evaluate with: python src/eval_f2.py <db> --variants

    # labelled window (neighbours leave-one-out from the same DB, illustrations decided before the window)
    python src/run_recall_pass.py data/eval_window.sqlite --before 2025-10-01
    # April-June, neighbours from the labelled window
    python src/run_recall_pass.py data/aprjun.sqlite --ref-db data/eval_window.sqlite --before 2026-04-01
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import examples, llm, recall_pass, triage  # noqa: E402


def candidates(con):
    rows = [dict(r) for r in con.execute(
        """SELECT j.slug, j.docket, j.decision_date, j.division, j.subject, j.text, a.ai_score
           FROM judgements j LEFT JOIN assessments a ON a.slug = j.slug""")]
    return [r for r in rows if triage.classify(r)["areas"]]


def references(ref_db):
    """Labelled candidates of the reference DB: picked = on Suva's Q4 2025 / Q1 2026 list."""
    gt = examples.load_ground_truth()
    summ = {ex["docket"]: ex["de"] for ex in examples.load_examples()}
    con = sqlite3.connect(ref_db)
    con.row_factory = sqlite3.Row
    refs = [{"docket": r["docket"], "subject": r["subject"] or "", "text": r["text"] or "",
             "picked": r["docket"] in gt, "summary": summ.get(r["docket"], "")} for r in candidates(con)]
    con.close()
    return refs


MONTHS = {m: i + 1 for i, names in enumerate([
    ("januar", "janvier", "gennaio"), ("februar", "février", "febbraio"), ("märz", "mars", "marzo"),
    ("april", "avril", "aprile"), ("mai", "maggio"), ("juni", "juin", "giugno"), ("juli", "juillet", "luglio"),
    ("august", "août", "agosto"), ("september", "septembre", "settembre"), ("oktober", "octobre", "ottobre"),
    ("november", "novembre"), ("dezember", "décembre", "dicembre")]) for m in names}


def _date_from_title(title):
    m = re.search(r"(\d{1,2})\.?\s*(?:er\s+)?([A-Za-zäéû]+)\s+(\d{4})", title or "")
    if not m or m.group(2).lower() not in MONTHS:
        return ""
    return f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"


def illustrations(before):
    """Suva summaries of the types the main triage misses (IV, procedural accident, daily allowance),
    decided before `before` (no label leakage on the evaluation window). Date from the summary's title,
    subject line from data/examples_compare.json or the crawled ruling in data/bger/."""
    subjects = {}
    p = os.path.join(ROOT, "data", "examples_compare.json")
    if os.path.exists(p):
        subjects = {x["docket"]: x.get("subject") or "" for x in json.load(open(p, encoding="utf-8"))["items"]}
    out = []
    for ex in examples.load_examples():
        d = _date_from_title(ex.get("title"))
        if not d or d >= before:
            continue
        subject = subjects.get(ex["docket"], "")
        f = os.path.join(ROOT, "data/bger", ex["docket"].replace("/", "_") + ".html")
        if not subject and os.path.exists(f):
            c = triage.classify({"text": re.sub("<[^>]+>", " ", open(f, encoding="utf-8", errors="ignore").read())})
        else:
            c = triage.classify({"subject": subject})
        if "invalidity" in c["areas"] or "daily_allowance" in c["areas"] or c["procedural"]:
            out.append(ex)
    return out[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--ref-db", help="labelled DB for the neighbours (default: the same DB, leave-one-out)")
    ap.add_argument("--before", required=True, help="only use Suva illustrations decided before this date")
    ap.add_argument("--low", type=int, default=0, help="main scores are mostly 0 or >= 60, so the default re-assesses every candidate below the cutoff")
    ap.add_argument("--high", type=int, default=60, help="main-triage cutoff; rulings at or above are already listed")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--no-neighbours", action="store_true")
    ap.add_argument("--no-illustrations", action="store_true")
    a = ap.parse_args()

    nb = None if a.no_neighbours else recall_pass.Neighbours(references(a.ref_db or a.db))
    if nb:
        print(f"{nb.n} labelled reference rulings ({sum(r['picked'] for r in nb.refs)} picked by Suva)")
    ill = [] if a.no_illustrations else illustrations(a.before)
    print(f"{len(ill)} illustrations: {', '.join(e['docket'] for e in ill)}")

    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS recall_assessments (slug TEXT PRIMARY KEY, score INTEGER, scores TEXT,
                   leading TEXT, reason_de TEXT, model TEXT, created_at TEXT)""")
    done = {r[0] for r in con.execute("SELECT slug FROM recall_assessments")}
    now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")  # noqa: E731
    cands = candidates(con)
    todo = []
    for r in cands:
        if r["slug"] in done:
            continue
        if a.low <= (r["ai_score"] or 0) < a.high:
            todo.append(r)
        else:  # outside the borderline: record the leading-case signals only (no LLM call)
            con.execute("INSERT OR REPLACE INTO recall_assessments VALUES (?,?,?,?,?,?,?)",
                        (r["slug"], None, "[]", json.dumps(recall_pass.leading_signals(r["text"]), ensure_ascii=False),
                         "", "rules", now()))
    con.commit()
    print(f"{len(cands)} candidates, {len(todo)} borderline ({a.low} <= score < {a.high}) to re-assess "
          f"x {a.samples} samples")

    def work(r):
        return r, recall_pass.assess(r, nb, ill, samples=a.samples)

    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(work, r) for r in todo]
        for f in as_completed(futs):
            try:
                r, res = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr)
                continue
            con.execute("INSERT OR REPLACE INTO recall_assessments VALUES (?,?,?,?,?,?,?)",
                        (r["slug"], res["score"], json.dumps(res["scores"]), json.dumps(res["leading"], ensure_ascii=False),
                         res["reason_de"], llm.model_name(), now()))
            con.commit()
            print(f"{r['docket']}: main={r['ai_score']} recall={res['scores']} lead={res['leading']}", flush=True)


if __name__ == "__main__":
    main()
