"""Let Apertus choose deciding-ground hashtags (suva/hashtags.py vocabulary) for every Apertus-scored ruling.

Stores keys in table reason_tags(slug, grounds JSON, outcome, model, created_at); finalize.py turns them
into tags / tags_fr.

    python src/run_hashtags.py data/aprjun.sqlite [--workers 4] [--redo]
"""
import argparse
import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import hashtags, llm  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS reason_tags (slug TEXT PRIMARY KEY, grounds TEXT, outcome TEXT, model TEXT, created_at TEXT)")
    con.commit()
    done = set() if a.redo else {r[0] for r in con.execute("SELECT slug FROM reason_tags")}
    rows = [dict(r) for r in con.execute("""SELECT j.slug, j.docket, j.subject, j.text, a.explanation_de FROM judgements j
                                            JOIN assessments a ON a.slug = j.slug WHERE a.model LIKE 'apertus%'""")]
    todo = [r for r in rows if r["slug"] not in done]
    print(f"{len(todo)} rulings to tag", flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(lambda r: (r, hashtags.choose(r, r["explanation_de"] or "")), r) for r in todo]
        for f in as_completed(futs):
            try:
                r, x = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            con.execute("INSERT OR REPLACE INTO reason_tags VALUES (?,?,?,?,?)",
                        (r["slug"], json.dumps(x["grounds"]), x["outcome"], llm.model_name(),
                         datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
            print(f"{r['docket']}: {x['grounds']} -> {x['outcome']}", flush=True)


if __name__ == "__main__":
    main()
