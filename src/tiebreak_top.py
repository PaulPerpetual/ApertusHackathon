"""Order the top of the list by a direct comparison (Apertus, one listwise call).

The ranking pass gives coarse importance values, so several rulings tie at the top score. The top 5 are what Suva's
lawyer reads, so Apertus compares the tied top rulings side by side and puts them in order; scores become
99, 98, 97, ... (Tier 1 range), and finalize/CSV/UI follow that order. Human overrides are never touched.

    python src/tiebreak_top.py data/aprjun.sqlite [--n 12]
"""
import argparse
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

SYSTEM = """Du leitest den Rechtsdienst der Suva (Unfallversicherer). Unten stehen Urteile des Bundesgerichts, die alle
als sehr wichtig eingestuft wurden. Ordne sie nach ihrer Wichtigkeit für die tägliche Praxis der Suva-Juristinnen:
zuerst das Urteil, das sie am dringendsten kennen müssen (neuer oder präzisierter Rechtssatz im Unfallversicherungsrecht,
breite Wirkung auf viele Fälle, Suva als Partei), zuletzt das am wenigsten dringende.
Antworte nur mit der Reihenfolge der Nummern, durch Kommas getrennt, z.B.: 3, 1, 4, 2"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--n", type=int, default=12, help="consider at most this many top rulings")
    a = ap.parse_args()
    os.environ["SUVA_DB"] = os.path.abspath(a.db)
    from suva import llm
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    top = con.execute("SELECT MAX(ai_score) FROM assessments WHERE tier = 1").fetchone()[0]
    rows = [dict(r) for r in con.execute("""SELECT a.slug, j.docket, a.title_de, a.explanation_de,
            (SELECT text FROM summaries s WHERE s.slug = a.slug AND s.lang = 'de') AS sum_de
            FROM assessments a JOIN judgements j ON j.slug = a.slug
            WHERE a.tier = 1 AND a.ai_score >= ? AND a.score_override IS NULL ORDER BY j.decision_date DESC""", (top - 2,))][:a.n]
    if len(rows) < 2:
        print("nothing to break")
        return
    listing = "\n\n".join(f"[{i + 1}] {r['docket']}: {r['title_de']}\nBegründung: {(r['explanation_de'] or '')[:350]}\n"
                          f"Zusammenfassung: {(r['sum_de'] or '')[:700]}" for i, r in enumerate(rows))
    order = []
    for _ in range(2):
        out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": listing}], temperature=0.0, max_tokens=80)
        nums = [int(x) for x in re.findall(r"\d+", out) if 1 <= int(x) <= len(rows)]
        order = list(dict.fromkeys(nums))
        if len(order) >= len(rows) - 1:
            break
    order += [i + 1 for i in range(len(rows)) if i + 1 not in order]  # anything the model skipped goes last
    for rank, idx in enumerate(order):
        r = rows[idx - 1]
        score = max(60, 99 - rank)
        con.execute("UPDATE assessments SET ai_score = ? WHERE slug = ?", (score, r["slug"]))
        con.execute("CREATE TABLE IF NOT EXISTS tiebreak (slug TEXT PRIMARY KEY, rank INTEGER, score INTEGER)")
        con.execute("INSERT OR REPLACE INTO tiebreak VALUES (?,?,?)", (r["slug"], rank + 1, score))
        print(f"{rank + 1:2}. {score}  {r['docket']}  {r['title_de'][:80]}")
    con.commit()


if __name__ == "__main__":
    main()
