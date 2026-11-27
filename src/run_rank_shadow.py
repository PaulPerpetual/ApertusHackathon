"""Run the shadow ranking (suva/rank_shadow.py) on a DB's hit list; results in rankings_shadow (live list untouched).

Hit list = assessments.tier in (1, 2) when tiers exist, else v1 selection (main >= 60 or IV pass >= 40).
After the pointwise sub-scores, the top --top rulings are ordered by one listwise Apertus call.

    python src/run_rank_shadow.py data/aprjun.sqlite [--workers 6] [--top 15]
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
from suva import llm, rank_shadow, triage  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS rankings_shadow (slug TEXT PRIMARY KEY, importance REAL, criteria TEXT, reason TEXT,
                   list_rank INTEGER, final REAL, model TEXT, created_at TEXT)""")
    con.commit()
    t = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    acols = {r[1] for r in con.execute("PRAGMA table_info(assessments)")}
    rows = [dict(r) for r in con.execute(f"""SELECT j.slug, j.docket, j.subject, j.text, a.title_de, a.explanation_de,
            {'COALESCE(f.main_score, a.ai_score)' if 'final_selection' in t else 'a.ai_score'} AS main,
            {'i.score' if 'iv_assessments' in t else 'NULL'} AS iv, {'a.tier' if 'tier' in acols else 'NULL'} AS tier,
            (SELECT text FROM summaries s WHERE s.slug = j.slug AND s.lang = 'de') AS sum_de
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            {'LEFT JOIN final_selection f ON f.slug = j.slug' if 'final_selection' in t else ''}
            {'LEFT JOIN iv_assessments i ON i.slug = j.slug' if 'iv_assessments' in t else ''}""")]
    hit = []
    for r in rows:
        c = triage.classify({"subject": r["subject"], "text": r["text"]})
        if not c["areas"]:
            continue
        on = r["tier"] in (1, 2) if r["tier"] is not None else ((r["main"] or 0) >= 60 or ("invalidity" in c["areas"] and (r["iv"] or 0) >= 40))
        if on:
            hit.append(r)
    done = {r[0] for r in con.execute("SELECT slug FROM rankings_shadow WHERE importance IS NOT NULL")}
    todo = [r for r in hit if r["slug"] not in done]
    print(f"{len(hit)} on the list, {len(todo)} to score", flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(lambda r: (r, rank_shadow.assess(r, r["explanation_de"] or "")), r) for r in todo]
        for f in as_completed(futs):
            try:
                r, x = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            con.execute("INSERT OR REPLACE INTO rankings_shadow (slug, importance, criteria, reason, model, created_at) VALUES (?,?,?,?,?,?)",
                        (r["slug"], x["importance"], json.dumps(x["criteria"]), x["reason"], llm.model_name(),
                         datetime.now(timezone.utc).isoformat(timespec="seconds")))
            con.commit()
    # listwise ordering of the top (tier 1 first, like production: Grenzfälle never above Tier 1)
    sc = {r[0]: (r[1], r[2]) for r in con.execute("SELECT slug, importance, reason FROM rankings_shadow")}
    hit = [r for r in hit if r["slug"] in sc]
    hit.sort(key=lambda r: (0 if r["tier"] in (1, None) else 1, -sc[r["slug"]][0]))
    top = hit[:a.top]
    order = rank_shadow.order_top([{"docket": r["docket"], "title": r["title_de"], "reason": sc[r["slug"]][1],
                                     "summary": r["sum_de"]} for r in top])
    for i, r in enumerate(hit):
        final = sc[r["slug"]][0]
        rank_in_top = None
        if i < len(top):
            rank_in_top = order.index(i) + 1
            final = 200 - rank_in_top  # top block first, in listwise order
        elif r["tier"] == 2:
            final = final - 100  # Grenzfälle below all Tier 1 (same rule as production)
        con.execute("UPDATE rankings_shadow SET list_rank=?, final=? WHERE slug=?", (rank_in_top, final, r["slug"]))
    con.commit()
    print("top after listwise ordering:", [top[k]["docket"] for k in order][:10])


if __name__ == "__main__":
    main()
