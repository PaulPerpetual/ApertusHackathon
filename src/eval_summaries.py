"""Compare summary variants against Suva's expert summaries (Codi's measures + style + error checks).

For each ruling in --only, with Suva's summary as reference:
  * proposition recovery (Apertus as open-weights judge): Suva's key legal points are extracted once;
    each candidate is judged covered / partial / missing per point, plus contradictions
  * automatic errors: outcome vs Dispositiv, invalid consideration refs, 'Suva' when Suva isn't a party,
    French abbreviations in German, anonymisation placeholders
  * style vs Suva: rule-first opening, present tense, words, sentence length, court mentions, refs

    python src/eval_summaries.py --only dev19.txt --variant pr16=data/ex_pr16.sqlite --variant v2=data/ex_v2.sqlite
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from statistics import median

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import erwaegungen, examples, llm  # noqa: E402

CACHE = os.path.join(ROOT, "data", "eval_gold_points.json")

GOLD_SYS = """Lies die Urteilszusammenfassung des Rechtsdienstes der Suva und liste ihre juristischen Kernaussagen auf:
die Rechtssätze und Ergebnisse, die eine Juristin daraus mitnehmen soll (2-6 Punkte, je ein kurzer Satz, keine
Sachverhaltsdetails). Antworte nur mit JSON: {"punkte": ["...", "..."]}"""

JUDGE_SYS = """Du prüfst eine Urteilszusammenfassung gegen eine Liste von Kernaussagen (Referenz: Suva-Juristin).
Für jede Kernaussage: "ja" (inhaltlich enthalten), "teilweise" oder "nein". Zusätzlich: Widerspricht die
Zusammenfassung einer Kernaussage oder dem Ergebnis? Antworte nur mit JSON:
{"bewertung": ["ja"|"teilweise"|"nein", ...], "widersprueche": ["<kurz>", ...]}"""

PRES = r"\b(ist|sind|hat|haben|muss|müssen|kann|können|darf|gilt|genügt|reicht|besteht|liegt|setzt|bedarf)\b"
PAST = r"\b(wurde|wurden|war|waren|hatte|hatten|erwog|wies|hiess|hielt|bestätigte|verneinte|bejahte|prüfte|stellte)\b"
FR_IN_DE = re.compile(r"\b(LAA|OLAA|LPGA|LAI|RAI|OAI|ESS|CNA|LTF)\b")


def gold_points(suva_de):
    for _ in range(2):
        try:
            a = llm.parse_json(llm.chat([{"role": "system", "content": GOLD_SYS}, {"role": "user", "content": suva_de}],
                                        temperature=0.0, max_tokens=500, json_mode=True))
            pts = [str(p) for p in a.get("punkte", [])][:6]
            if pts:
                return pts
        except ValueError:
            pass
    return []


def judge(points, summary):
    user = "Kernaussagen:\n" + "\n".join(f"{i + 1}. {p}" for i, p in enumerate(points)) + f"\n\nZusammenfassung:\n{summary}"
    for _ in range(2):
        try:
            a = llm.parse_json(llm.chat([{"role": "system", "content": JUDGE_SYS}, {"role": "user", "content": user}],
                                        temperature=0.0, max_tokens=400, json_mode=True))
            marks = [str(x).lower() for x in a.get("bewertung", [])][:len(points)]
            if len(marks) == len(points):
                return marks, [str(x) for x in a.get("widersprueche", []) if str(x).strip()]
        except ValueError:
            pass
    return None, []


def style(t):
    s = [x for x in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", (t or "").strip()) if x]
    first = s[0] if s else ""
    fact = bool(re.search(r"^(Der|Die|Ein|Eine)\s+(Versichert|Beschwerdef)|erlitt|geboren|arbeitete", first))
    court = bool(re.match(r"(Das Bundesgericht|Das BGer|In diesem Urteil)", first))
    return {"words": len((t or "").split()), "words_per_sentence": len((t or "").split()) / max(1, len(s)),
            "rule_first": not fact and not court, "present": len(re.findall(PRES, t or "")) > len(re.findall(PAST, t or "")),
            "court_mentions": len(re.findall(r"Bundesgericht|BGer", t or "")),
            "refs": len(re.findall(r"\((?:E\.|Erw\.)", t or ""))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", required=True)
    ap.add_argument("--variant", action="append", required=True, help="name=path/to.sqlite")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "eval_summaries.json"))
    a = ap.parse_args()
    dockets = [l.strip() for l in open(a.only) if l.strip()]
    ex = {e["docket"]: e for e in examples.load_examples()}
    variants = dict(v.split("=", 1) for v in a.variant)
    texts, summ = {}, {}
    for name, path in variants.items():
        con = sqlite3.connect(path)
        for d, t, lang, s in con.execute("SELECT j.docket, j.text, s.lang, s.text FROM summaries s JOIN judgements j ON j.slug = s.slug"):
            if lang == "de":
                summ.setdefault(name, {})[d] = s
                texts[d] = t
    dockets = [d for d in dockets if d in ex and all(d in summ.get(n, {}) for n in variants)]
    print(f"{len(dockets)} rulings with all variants")
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    todo = [d for d in dockets if d not in cache]
    with ThreadPoolExecutor(4) as pool:
        cache.update(dict(zip(todo, pool.map(lambda d: gold_points(ex[d]["de"]), todo))))
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=1)  # written once, after the threads
    golds = {d: cache[d] for d in dockets}
    dockets = [d for d in dockets if golds[d]]
    rows = {}
    for name in variants:
        with ThreadPoolExecutor(4) as pool:
            judged = dict(zip(dockets, pool.map(lambda d: judge(golds[d], summ[name][d]), dockets)))
        per = []
        for d in dockets:
            s, t = summ[name][d], texts[d]
            marks, contra = judged[d]
            score = (sum(1.0 if m.startswith("ja") else 0.5 if m.startswith("teil") else 0.0 for m in marks) / len(marks)) if marks else None
            per.append({"docket": d, "recovery": score, "contradictions": contra,
                        "outcome_error": bool(erwaegungen.outcome_conflict(s, t)),
                        "bad_refs": bool(erwaegungen.check_refs(s, erwaegungen.numbers(t))[1]),
                        "wrong_suva": bool(re.search(r"\bSuva\b", s)) and not re.search(r"\b(Suva|SUVA|CNA|INSAI)\b|Unfallversicherungsanstalt|Caisse nationale", t),
                        "fr_abbrev_in_de": bool(FR_IN_DE.search(s)), "placeholder": bool(re.search(r"\b[A-Z]\._{3,}", s)),
                        **style(s)})
        rows[name] = per
    suva_style = [style(ex[d]["de"]) for d in dockets]

    def agg(per, k, f=median):
        v = [p[k] for p in per if p[k] is not None]
        return round(f(v), 3) if v else None
    share = lambda per, k: round(sum(bool(p[k]) for p in per) / len(per), 2)  # noqa: E731
    print(f"\n{'measure':32}" + "".join(f"{n:>12}" for n in rows) + f"{'Suva':>12}")
    lines = [("Suva points recovered (mean)", lambda p: agg(p, "recovery", lambda v: sum(v) / len(v)), None),
             ("rulings with contradictions", lambda p: sum(bool(x["contradictions"]) for x in p), None),
             ("outcome errors", lambda p: sum(x["outcome_error"] for x in p), None),
             ("invalid refs", lambda p: sum(x["bad_refs"] for x in p), None),
             ("'Suva' not a party", lambda p: sum(x["wrong_suva"] for x in p), None),
             ("French abbrev. in German", lambda p: sum(x["fr_abbrev_in_de"] for x in p), None),
             ("placeholders", lambda p: sum(x["placeholder"] for x in p), None),
             ("rule-first opening", lambda p: share(p, "rule_first"), lambda: share(suva_style, "rule_first")),
             ("present tense", lambda p: share(p, "present"), lambda: share(suva_style, "present")),
             ("words (median)", lambda p: agg(p, "words"), lambda: agg(suva_style, "words")),
             ("words/sentence (median)", lambda p: agg(p, "words_per_sentence"), lambda: agg(suva_style, "words_per_sentence")),
             ("court mentions (median)", lambda p: agg(p, "court_mentions"), lambda: agg(suva_style, "court_mentions")),
             ("Erw. refs (median)", lambda p: agg(p, "refs"), lambda: agg(suva_style, "refs"))]
    table = {}
    for label, f, fs in lines:
        vals = {n: f(per) for n, per in rows.items()}
        table[label] = {**vals, "Suva": fs() if fs else None}
        print(f"{label:32}" + "".join(f"{str(vals[n]):>12}" for n in rows) + f"{str(fs() if fs else ''):>12}")
    json.dump({"dockets": dockets, "gold": golds, "table": table, "per_ruling": rows}, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
