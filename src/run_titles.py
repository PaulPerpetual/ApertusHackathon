"""Short, complete DE/FR titles for rulings whose title is cut off or too long.

Titles were hard-cut at 120 characters (triage and relabel), so many ended mid-word. Apertus writes both
titles in one call (max. 12 words each); a title is saved only if it passes checks: <= 100 characters,
right language, no case/BGE/ATF numbers (the model invented some once), not identical across languages.

    python src/run_titles.py data/aprjun.sqlite [--workers 3] [--all]
"""
import argparse
import os
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import llm  # noqa: E402

SYSTEM = """Du schreibst Titel für Urteile des Bundesgerichts im Stil der Suva-Urteilsübersicht.
Regeln für beide Sprachen:
- höchstens 12 Wörter, vollständig (nie abgebrochen), kein Punkt am Ende;
- nennt die Rechtsfrage und das Ergebnis, z.B. "Komplementärrente: IV-Rente nur anteilmässig anzurechnen";
- keine Urteils-, BGE- oder ATF-Nummern, keine Daten, keine Namen; nicht mit "Bundesgericht" beginnen;
- Fachsprache: deutsch wie in BGE (UVG, IVG, ATSG), französisch wie in ATF (LAA, LAI, LPGA); französisch eigenständig formuliert.
Antworte genau so:
DE: <deutscher Titel>
FR: <titre français>"""

NUMS = re.compile(r"\d[A-Z]_\d+/\d{4}|\bBGE\s*\d|\bATF\s*\d|\bBGer\s+\d")
FRW = re.compile(r"\b(le|la|les|des|du|selon|à|aux|est|pour|une?|l'|d')\b", re.I)
DEW = re.compile(r"\b(der|die|das|dem|den|und|bei|nach|für|ist|zur|zum|eine?|im|vom|keine?)\b", re.I)


def bad(t):
    return not t or len(t) >= 118 or not t.rstrip().endswith(tuple(".)»\"") + tuple("abcdefghijklmnopqrstuvwxyzäöüéèàç0123456789%")) \
        or len(t) > 100


def lang_ok(lang, t):
    f, d = len(FRW.findall(t)), len(DEW.findall(t))
    return f <= d + 1 if lang == "de" else d <= f + 1


def make(row):
    user = (f"Bisheriger Titel (evtl. abgeschnitten): {row['title_de'] or row['title_fr']}\n"
            f"Rechtsgebiet: {row['subject']}\nBegründung: {(row['explanation_de'] or '')[:700]}")
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    for _ in range(2):
        out = llm.chat(msgs, temperature=0.1, max_tokens=120)
        m = re.search(r"DE\s*:\s*(.+?)\s*\n\s*FR\s*:\s*(.+)", out.strip(), re.S)
        if not m:
            continue
        de, fr = (x.strip().strip('"«»„“').split("\n")[0].rstrip(".") for x in m.groups())
        problems = [p for p, cond in (("length", len(de) > 100 or len(fr) > 100), ("numbers", NUMS.search(de + " " + fr)),
                                      ("language", not lang_ok("de", de) or not lang_ok("fr", fr)), ("same", de == fr)) if cond]
        if not problems:
            return de, fr, None
        msgs += [{"role": "assistant", "content": out},
                 {"role": "user", "content": f"Problem: {', '.join(problems)}. Kürzer, ohne Nummern, richtige Sprache. Gleiches Format."}]
    return None, None, "checks failed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--all", action="store_true", help="redo every Apertus-scored title, not only cut/long ones")
    a = ap.parse_args()
    con = sqlite3.connect(a.db, timeout=30)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("""SELECT a.slug, j.docket, j.subject, a.title_de, a.title_fr, a.explanation_de
            FROM assessments a JOIN judgements j ON j.slug = a.slug WHERE a.model LIKE 'apertus%'""")]
    todo = [r for r in rows if a.all or bad(r["title_de"]) or bad(r["title_fr"])]
    print(f"{len(todo)} of {len(rows)} titles to redo", flush=True)
    ok = 0
    with ThreadPoolExecutor(a.workers) as pool:
        for f in as_completed([pool.submit(lambda r: (r, make(r)), r) for r in todo]):
            try:
                r, (de, fr, err) = f.result()
            except Exception as e:  # noqa: BLE001
                print("!", e, file=sys.stderr, flush=True)
                continue
            if err:
                print(f"! {r['docket']}: {err}, kept old title", flush=True)
                continue
            con.execute("UPDATE assessments SET title_de=?, title_fr=? WHERE slug=?", (de, fr, r["slug"]))
            con.commit()
            ok += 1
            print(f"{r['docket']}: {de} | {fr}", flush=True)
    print(f"{ok} titles replaced")


if __name__ == "__main__":
    main()
