"""Rebuild the labelled evaluation DB without anybody's local copy: candidates and Apertus v1 scores come from
data/runs/window (in the repo), ruling texts from entscheidsuche.ch (cached under data/period/window_cache/).

    python src/build_eval_db.py data/eval_window.sqlite
    python src/build_eval_db.py data/aprjun_local.sqlite aprjun     # same for April-June (data/runs/aprjun), unlabelled

Then: python src/run_recall_pass.py data/eval_window.sqlite --before 2025-10-01
      python src/eval_f2.py data/eval_window.sqlite --variants
iv_assessments gets score 40 for rulings v1 selected only via the IV second pass (main score below 60), so the
production rule "main >= 60 or IV pass >= 40" reproduces the v1 list exactly.
"""
import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import crawl_period  # noqa: E402
from suva import scraper  # noqa: E402

DATASET = sys.argv[2] if len(sys.argv) > 2 else "window"
RUNS = os.path.join(ROOT, "data", "runs", DATASET)
CACHE = os.path.join(ROOT, "data", "period", f"{DATASET}_cache")


def fetch(docket):
    ids = crawl_period.find_case(docket)
    if not ids:
        return docket, None, None
    row, _ = crawl_period.download(ids[0], CACHE)
    raw = open(os.path.join(CACHE, f"{ids[0]}.html"), encoding="utf-8", errors="ignore").read()
    return docket, row, scraper._html_text(raw)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "eval_window.sqlite")
    os.makedirs(CACHE, exist_ok=True)
    meta = json.load(open(os.path.join(RUNS, "_dockets.json"), encoding="utf-8"))
    v1 = {r["docket"]: r for r in map(json.loads, open(os.path.join(RUNS, "apertus70b-v1.jsonl"), encoding="utf-8"))
          if "docket" in r}
    con = sqlite3.connect(out)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS judgements (slug TEXT PRIMARY KEY, docket TEXT, decision_date TEXT, division TEXT,
                                               subject TEXT, text TEXT);
        CREATE TABLE IF NOT EXISTS assessments (slug TEXT PRIMARY KEY, ai_score INTEGER, prefilter_score INTEGER,
                                                model TEXT, explanation_de TEXT);
        CREATE TABLE IF NOT EXISTS iv_assessments (slug TEXT PRIMARY KEY, score INTEGER, principle TEXT, reason_de TEXT,
                                                   model TEXT, created_at TEXT);""")
    have = {r[0] for r in con.execute("SELECT docket FROM judgements WHERE length(text) > 0")}
    todo = [d for d in meta if d not in have]
    print(f"{len(meta)} candidates, {len(todo)} texts to fetch")
    with ThreadPoolExecutor(4) as pool:
        for i, (docket, row, text) in enumerate(pool.map(fetch, todo), 1):
            if text is None:
                print("! not found:", docket)
                continue
            m, r = meta[docket], v1.get(docket, {})
            slug = docket.replace("/", "_")
            con.execute("INSERT OR REPLACE INTO judgements VALUES (?,?,?,?,?,?)",
                        (slug, docket, m.get("date") or row["decision_date"], docket.split("_")[0], m.get("subject"), text))
            con.execute("INSERT OR REPLACE INTO assessments VALUES (?,?,?,?,?)",
                        (slug, r.get("score", 0), 20, "apertus-v1-5-70b (run apertus70b-v1)", r.get("reason", "")))
            if r.get("relevant") and r.get("score", 0) < 60:
                con.execute("INSERT OR REPLACE INTO iv_assessments VALUES (?,?,?,?,?,?)",
                            (slug, 40, "", "selected by the v1 IV second pass", "apertus70b-v1", ""))
            if i % 25 == 0:
                con.commit()
                print(f"  {i}/{len(todo)}", flush=True)
    con.commit()
    n = con.execute("SELECT count(*) FROM judgements").fetchone()[0]
    print(f"{n} rulings in {out}")


if __name__ == "__main__":
    main()
