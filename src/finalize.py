"""Finalise a triaged DB: selection rule, decision-criteria hashtags, Suva hit list.

Selection (tuned for F2 on the labelled Oct 2025 - Mar 2026 window, see src/eval_f2.py):
  selected  = Apertus main score >= 60
              OR (invalidity ruling AND Apertus IV second pass >= 40)   [union rule, F2 0.736]
An invalidity ruling promoted by the second pass gets ai_score = 60 and a note in its explanation,
so the UI list and the hit list agree. Both scores are Apertus outputs; originals are kept in
table final_selection (idempotent: re-running starts from the stored originals).

Tags: controlled vocabulary (suva/hashtags.py): subject area, 2-3 deciding grounds chosen by Apertus, outcome.
Stored without '#' (the UI adds it); DE in tags, FR in tags_fr (same order). Selection lives in final_selection.

Writes data/submission/hitlist_<from>_<to>.txt in Suva's format: "8C_691/2024, 9C_612/2025, ...".

    python src/finalize.py data/aprjun.sqlite --from 2026-04-01 --to 2026-06-30
"""
import argparse
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import hashtags, triage  # noqa: E402

MAIN_CUTOFF = 60
IV_CUTOFF = 40


def hashtag(s):
    s = re.sub(r"[^\wÄÖÜäöüÀ-ÿ-]+", "", str(s).strip().replace(" ", "-"))
    return "#" + s if s and not s.startswith("#") else s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--from", dest="date_from", required=True)
    ap.add_argument("--to", dest="date_to", required=True)
    ap.add_argument("--rewrite-text", action="store_true",
                    help="also rewrite tags and explanations from reason_tags / explanations. Default: selection only, "
                         "so texts from `python -m suva relabel` (Paul's house style) and human edits are kept")
    ap.add_argument("--recall-pass", type=int, metavar="CUTOFF", default=None,
                    help="also select rulings the recall pass (src/run_recall_pass.py) scored >= CUTOFF, and five-judge "
                         "rulings. Off by default; turn on once `eval_f2.py --variants` shows a better F2")
    ap.add_argument("--adj-table", default="adjudications", help="pass-4 table (adjudications_v2 = adapted prompt)")
    ap.add_argument("--tiers", action="store_true",
                    help="Tier 1 = v1; Tier 2 'Grenzfall' = other candidates kept by pass 4 (src/run_adjudicate.py); "
                         "hit list = Tier 1+2 minus status 'rejected' / score override < 40, plus overrides >= 60")
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS final_selection (slug TEXT PRIMARY KEY, main_score INTEGER,
                   iv_score INTEGER, selected INTEGER, rule TEXT, orig_tags TEXT, orig_expl_de TEXT, orig_expl_fr TEXT)""")
    for ddl in ("CREATE TABLE IF NOT EXISTS reason_tags (slug TEXT PRIMARY KEY, grounds TEXT, outcome TEXT, model TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS explanations (slug TEXT PRIMARY KEY, de TEXT, fr TEXT, model TEXT, created_at TEXT)"):
        con.execute(ddl)
    con.execute("CREATE TABLE IF NOT EXISTS recall_assessments (slug TEXT PRIMARY KEY, score INTEGER, scores TEXT,"
                " leading TEXT, reason_de TEXT, model TEXT, created_at TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS iv_assessments (slug TEXT PRIMARY KEY, score INTEGER, principle TEXT,"
                " reason_de TEXT, model TEXT, created_at TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS adjudications (slug TEXT PRIMARY KEY, tier INTEGER, reason TEXT, model TEXT, created_at TEXT)")
    acols = {r[1] for r in con.execute("PRAGMA table_info(assessments)")}
    for name, ddl in (("tier", "INTEGER"), ("tier_reason", "TEXT")):  # same migration as db._migrate
        if name not in acols:
            con.execute(f"ALTER TABLE assessments ADD COLUMN {name} {ddl}")
    con.execute("CREATE TABLE IF NOT EXISTS rankings (slug TEXT PRIMARY KEY, importance INTEGER, reason TEXT, model TEXT, created_at TEXT)")
    con.execute(f"CREATE TABLE IF NOT EXISTS {a.adj_table} (slug TEXT PRIMARY KEY, tier INTEGER, reason TEXT, model TEXT, created_at TEXT)")
    rows = [dict(r) for r in con.execute(f"""
        SELECT j.slug, j.docket, j.decision_date, j.subject, j.text, COALESCE(j.status, 'new') AS status,
               a.score_override, a.tags_fr, a.ai_score, a.tags, a.suva_party, a.model,
               ad.tier AS adj_tier, ad.reason AS adj_reason, rk.importance AS importance,
               a.explanation_de, a.explanation_fr, i.score AS iv, i.principle,
               f.main_score AS f_main, f.orig_tags, f.orig_expl_de, f.orig_expl_fr,
               rc.score AS rc_score, rc.leading AS rc_leading, rt.grounds AS rt_grounds, rt.outcome AS rt_outcome, ex.de AS ex_de, ex.fr AS ex_fr
        FROM judgements j JOIN assessments a ON a.slug = j.slug
        LEFT JOIN reason_tags rt ON rt.slug = j.slug LEFT JOIN explanations ex ON ex.slug = j.slug
        LEFT JOIN recall_assessments rc ON rc.slug = j.slug
        LEFT JOIN iv_assessments i ON i.slug = j.slug LEFT JOIN final_selection f ON f.slug = j.slug
        LEFT JOIN {a.adj_table} ad ON ad.slug = j.slug LEFT JOIN rankings rk ON rk.slug = j.slug""")]
    con.execute("CREATE TABLE IF NOT EXISTS tiebreak (slug TEXT PRIMARY KEY, rank INTEGER, score INTEGER)")
    tiebreak = dict(con.execute("SELECT slug, score FROM tiebreak").fetchall())
    hit = []
    for r in rows:
        main_score = r["f_main"] if r["f_main"] is not None else r["ai_score"]
        tags0 = json.loads(r["orig_tags"] if r["orig_tags"] is not None else (r["tags"] or "[]"))
        expl_de = r["orig_expl_de"] if r["orig_expl_de"] is not None else r["explanation_de"]
        expl_fr = r["orig_expl_fr"] if r["orig_expl_fr"] is not None else r["explanation_fr"]
        if r["ex_de"]:  # specific explanation (src/run_explanations.py) replaces the first-pass text
            expl_de, expl_fr = r["ex_de"], r["ex_fr"] or expl_fr
        c = triage.classify({"subject": r["subject"], "text": r["text"]})
        iv_flag = "invalidity" in c["areas"] and r["iv"] is not None and r["iv"] >= IV_CUTOFF
        rc_flag = a.recall_pass is not None and (
            (r["rc_score"] or 0) >= a.recall_pass or bool(json.loads(r["rc_leading"] or "[]")))
        selected = (main_score or 0) >= MAIN_CUTOFF or iv_flag or rc_flag
        rule = "main" if (main_score or 0) >= MAIN_CUTOFF else ("iv_pass" if iv_flag else ("recall_pass" if rc_flag else ""))
        score = main_score
        if rule == "recall_pass":
            score = MAIN_CUTOFF
            expl_de = (expl_de or "") + " — Zweitprüfung (Apertus): in der zweiten Durchsicht als relevant eingestuft."
            expl_fr = (expl_fr or "") + " — Second examen (Apertus): jugé pertinent lors du second examen."
        if rule == "iv_pass":
            score = MAIN_CUTOFF
            expl_de = (expl_de or "") + f" — IV-Zweitprüfung (Apertus): {r['principle'] or 'übertragbarer Grundsatz'}"
            expl_fr = (expl_fr or "") + " — Second examen AI (Apertus): principe transposable à l'assurance-accidents."
        if r["rt_grounds"] is not None:  # controlled vocabulary chosen by Apertus (src/run_hashtags.py)
            tags, tags_fr = hashtags.compose(c["areas"], json.loads(r["rt_grounds"]), r["rt_outcome"])
        elif (r["model"] or "").startswith(("apertus", "mock")):
            tags, tags_fr = hashtags.compose(c["areas"], [], None)
        else:
            tags, tags_fr = [str(t).lstrip("#") for t in tags0], []
        con.execute("INSERT OR REPLACE INTO final_selection VALUES (?,?,?,?,?,?,?,?)",
                    (r["slug"], main_score, r["iv"], int(selected), rule, json.dumps(tags0, ensure_ascii=False),
                     r["explanation_de"] if r["orig_expl_de"] is None else r["orig_expl_de"],
                     r["explanation_fr"] if r["orig_expl_fr"] is None else r["orig_expl_fr"]))
        if a.rewrite_text:
            con.execute("UPDATE assessments SET ai_score=?, tags=?, tags_fr=?, explanation_de=?, explanation_fr=? WHERE slug=?",
                        (score, json.dumps(tags, ensure_ascii=False), json.dumps(tags_fr, ensure_ascii=False),
                         expl_de, expl_fr, r["slug"]))
        else:
            con.execute("UPDATE assessments SET ai_score=? WHERE slug=?", (score, r["slug"]))
        if a.tiers:
            tier, tier_reason = None, None
            if c["areas"]:
                if (main_score or 0) >= MAIN_CUTOFF or iv_flag:
                    tier = 1
                elif r["adj_tier"] in (1, 2):
                    tier, tier_reason = 2, r["adj_reason"]
                else:
                    tier, tier_reason = 3, r["adj_reason"]
            cur = con.execute("SELECT tags, tags_fr, explanation_de, explanation_fr FROM assessments WHERE slug=?", (r["slug"],)).fetchone()
            t_de = [t for t in json.loads(cur["tags"] or "[]") if t != "Grenzfall"]
            t_fr = [t for t in json.loads(cur["tags_fr"] or "[]") if t != "Cas limite"]
            e_de, e_fr = cur["explanation_de"] or "", cur["explanation_fr"] or ""
            e_de = re.sub(r"^Grenzfall – .*$", "", e_de, flags=re.S).strip() or e_de
            if tier == 2:  # mark the Grenzfall: first tag, prefixed reasoning, score below every Tier 1 ruling
                t_de, t_fr = ["Grenzfall"] + t_de, (["Cas limite"] + t_fr) if t_fr else t_fr
                why = re.sub(r"^\s*(Grenzfall|Tier\s*\d)\s*[,:–-]?\s*", "", tier_reason or "", flags=re.I).strip()
                why = why or "In der Zweitprüfung als möglicherweise relevant eingestuft."
                e_de = f"Grenzfall – {why}"
                if not e_fr.startswith("Cas limite"):
                    e_fr = "Cas limite – " + e_fr
                score = 50
            elif e_fr.startswith("Cas limite – "):
                e_fr = e_fr[len("Cas limite – "):]
            # ranking (pass 5, src/run_rank_pass.py): Tier 1 -> 60-99, Grenzfall -> 20-59, so sorting by score = our rank
            if r["importance"] is not None and tier == 1:
                score = 60 + round(r["importance"] * 0.39)
            if tier == 1 and r["slug"] in tiebreak:  # direct comparison of the top (src/tiebreak_top.py)
                score = tiebreak[r["slug"]]
            elif r["importance"] is not None and tier == 2:
                score = 20 + round(r["importance"] * 0.39)
            con.execute("UPDATE assessments SET tier=?, tier_reason=?, ai_score=?, tags=?, tags_fr=?, explanation_de=?, explanation_fr=? "
                        "WHERE slug=?", (tier, tier_reason, score, json.dumps(t_de, ensure_ascii=False),
                                         json.dumps(t_fr, ensure_ascii=False), e_de, e_fr, r["slug"]))
            # human decisions win: 'Nicht relevant' (status rejected) or a score override
            selected = tier in (1, 2)
            if r["score_override"] is not None:
                selected = r["score_override"] >= MAIN_CUTOFF
            if r["status"] == "rejected":
                selected = False
            con.execute("UPDATE final_selection SET selected=?, rule=? WHERE slug=?",
                        (int(selected), {1: rule or "main", 2: "grenzfall"}.get(tier, rule), r["slug"]))
        if selected and a.date_from <= (r["decision_date"] or "") <= a.date_to:
            hit.append(r["docket"])
    con.commit()

    def key(d):
        ch, n, y = re.match(r"(\d[A-Z])_(\d+)/(\d{4})", d).groups()
        return (ch, int(y), int(n))
    hit = sorted(set(hit), key=key)
    if a.tiers:  # ranked list for Suva: rank, ruling, Normal/Grenzfall, score (same order as the UI)
        import csv
        ranked = con.execute("""SELECT j.docket, j.decision_date, a.tier, COALESCE(a.score_override, a.ai_score) AS score, a.title_de
            FROM judgements j JOIN assessments a ON a.slug = j.slug JOIN final_selection f ON f.slug = j.slug
            WHERE f.selected = 1 AND j.decision_date BETWEEN ? AND ? ORDER BY score DESC, j.decision_date DESC""",
                             (a.date_from, a.date_to)).fetchall()
        path = os.path.join(ROOT, "data", "submission", f"hitlist_ranked_{a.date_from}_{a.date_to}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["rank", "urteil", "kategorie", "score", "entscheid", "titel"])
            for i, r in enumerate(ranked, 1):
                w.writerow([i, r["docket"], "Grenzfall" if r["tier"] == 2 else "normal", r["score"], r["decision_date"], r["title_de"]])
        print(f"ranked list -> {path}")
    os.makedirs(os.path.join(ROOT, "data", "submission"), exist_ok=True)
    out = os.path.join(ROOT, "data", "submission", f"hitlist_{a.date_from}_{a.date_to}.txt")
    open(out, "w").write(", ".join(hit) + "\n")
    print(f"{len(hit)} rulings on the hit list -> {out}")
    print(f"  via main score: {sum(1 for r in con.execute('SELECT rule FROM final_selection WHERE rule=?', ('main',)))}"
          f", via IV second pass: {sum(1 for r in con.execute('SELECT rule FROM final_selection WHERE rule=?', ('iv_pass',)))}"
          f", via recall pass: {sum(1 for r in con.execute('SELECT rule FROM final_selection WHERE rule=?', ('recall_pass',)))}")
    if a.tiers:
        print("  tiers:", dict(con.execute("SELECT COALESCE(tier, 0), COUNT(*) FROM assessments GROUP BY tier").fetchall()),
              "| Grenzfall on list:", con.execute("SELECT COUNT(*) FROM final_selection WHERE rule='grenzfall' AND selected=1").fetchone()[0])


if __name__ == "__main__":
    main()
