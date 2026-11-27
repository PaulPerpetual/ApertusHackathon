"""Derive Suva's relevance vocabulary from labelled examples.

Positives: rulings on Suva's list (judgements/BG_Urteile_2025_Q4_2026_Q1.xlsx).
Negatives: every other chamber 8/9 ruling decided in the same window (Oct 2025 - Mar 2026),
i.e. the social-law rulings Suva saw published and did NOT summarise.

For each term (word, two-word phrase, statute reference like "Art. 6 UVG") we compare
document frequency in positives vs negatives with a smoothed log-odds ratio, per language.
Output:
  data/terms_derived.csv        every scored term
  data/terms_derived.txt        the top terms, in prefilter.py's terms-file format
plus a printed evaluation of subject-area and term rules (recall / precision on the window).

    python src/derive_terms.py
"""
import collections
import csv
import glob
import html
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from prefilter import SUBJECT, SUBJECT_AREAS  # noqa: E402

WINDOW = os.path.join(ROOT, "data", "period", "2025-10-01_2026-03-31_ch89", "rulings")
POS_LIST = os.path.join(ROOT, "data", "bger", "index.csv")
CASE = re.compile(r"CH_BGer_\d{3}_(\d[A-Z])-(\d+)-(\d{4})_")
STATUTE = re.compile(r"\bArt\.\s*\d+[a-z]?(?:\s*(?:Abs|al|cpv)\.\s*\d+)?(?:\s*(?:lit|let)\.\s*[a-z])?\s+([A-Z][A-Za-z]{1,6})\b")
WORD = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'-]{2,}")
STOP = set("""der die das und des den dem ein eine einer eines nicht mit von zu zur zum auf für ist sich als auch
bei aus wird werden wurde wurden sind hat haben oder dass vom im in an es sie er ihr ihre ihren ihrem seiner
seine seinen sein kann können nach durch noch nur wie so bzw sowie diese dieser dieses vor über unter wenn
les des une est que qui dans pour par sur pas aux ses son sont été être ont avec cette elle sans plus ainsi
del della che per con non sono gli dei alla nel nella una""".split())


def plain(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    raw = re.sub(r"(?s)<(script|style).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", raw))).strip()


def strip_parties(t):
    """Drop the header up to the subject line: names of judges/lawyers/parties are noise."""
    m = SUBJECT.search(t[:6000])
    return t[m.start():] if m else t


def features(t):
    words = [w.lower() for w in WORD.findall(t)]
    feats = {w for w in words if w not in STOP}
    feats |= {f"{a} {b}" for a, b in zip(words, words[1:]) if a not in STOP and b not in STOP}
    feats |= {f"[law] {m}" for m in STATUTE.findall(t)}
    # insurer named as a party (Suva is never anonymised; private insurers usually are)
    if re.search(r"\b(Suva|SUVA|CNA|INSAI)\b", t):
        feats.add("[insurer] Suva/CNA/INSAI")
    return feats


def positives():
    pos = set()
    for r in csv.DictReader(open(POS_LIST)):
        if "spreadsheet" in r["sources"]:
            pos.add(r["case"])
    return pos


def main():
    pos_cases = positives()
    docs, files = [], {}
    for f in sorted(glob.glob(os.path.join(WINDOW, "*.html"))):
        m = CASE.search(os.path.basename(f))
        case = f"{m[1]}_{m[2]}/{m[3]}"
        # entscheidsuche can hold several files per case number: keep the longest text
        if case not in files or os.path.getsize(f) > os.path.getsize(files[case]):
            files[case] = f
    for case, f in sorted(files.items()):
        meta = json.load(open(f[:-5] + ".json"))
        t = plain(f)
        sm = SUBJECT.search(t[:6000])
        subject = sm.group(2) if sm else ""
        docs.append({"case": case, "lang": meta.get("Sprache", "?"), "label": case in pos_cases,
                     "areas": {a for a, p in SUBJECT_AREAS.items() if re.search(p, subject, re.I)},
                     "subject": subject, "feats": features(strip_parties(t))})
    n_pos = sum(d["label"] for d in docs)
    found = {d["case"] for d in docs if d["label"]}
    print(f"window: {len(docs)} chamber-8/9 rulings, {n_pos} on Suva's list "
          f"(missing from window: {sorted(pos_cases - found)})")

    # --- 1. how far do subject areas alone get us? ---
    proc = re.compile(r"Prozessvoraussetzung|recevabilit|retrait du recours|Rückzug|Nichteintreten|"
                      r"irrecevab|Revision|unentgeltlich|assistance judiciaire|Rechtsverzögerung", re.I)
    for d in docs:
        d["procedural"] = bool(proc.search(d["subject"]))
    print("\naccident rulings      on list / all")
    for kind in (False, True):
        sel = [d for d in docs if "accident" in d["areas"] and d["procedural"] == kind]
        print(f"  {'procedural only' if kind else 'on the merits':18} {sum(d['label'] for d in sel):4} / {len(sel):4}")
    print("\nsubject area      on list / all   share")
    for area in list(SUBJECT_AREAS) + ["(none)"]:
        sel = [d for d in docs if (area in d["areas"]) or (area == "(none)" and not d["areas"])]
        k = sum(d["label"] for d in sel)
        print(f"  {area:16} {k:4} / {len(sel):4}   {k / max(len(sel), 1):.0%}")

    # --- 2. discriminative terms, per language ---
    rows = []
    for lang in ("de", "fr", "it"):
        L = [d for d in docs if d["lang"] == lang]
        P = [d for d in L if d["label"]]
        N = [d for d in L if not d["label"]]
        if len(P) < 3:
            continue
        dp, dn = collections.Counter(), collections.Counter()
        for d in P:
            dp.update(d["feats"])
        for d in N:
            dn.update(d["feats"])
        for term, a in dp.items():
            if a < max(3, 0.15 * len(P)):
                continue
            b = dn.get(term, 0)
            # smoothed log-odds of a document containing the term, positives vs negatives
            lo = math.log((a + 0.5) / (len(P) - a + 0.5)) - math.log((b + 0.5) / (len(N) - b + 0.5))
            se = math.sqrt(1 / (a + .5) + 1 / (len(P) - a + .5) + 1 / (b + .5) + 1 / (len(N) - b + .5))
            rows.append({"lang": lang, "term": term, "pos_df": f"{a}/{len(P)}", "neg_df": f"{b}/{len(N)}",
                         "pos_rate": round(a / len(P), 3), "neg_rate": round(b / max(len(N), 1), 3),
                         "log_odds": round(lo, 2), "z": round(lo / se, 2)})
    rows.sort(key=lambda r: -r["z"])
    out = os.path.join(ROOT, "data", "terms_derived.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for lang in ("de", "fr"):
        print(f"\ntop terms [{lang}]   (share of Suva's picks containing it vs share of the others)")
        for r in [r for r in rows if r["lang"] == lang][:30]:
            print(f"  {r['term']:42} {r['pos_rate']:5.0%} vs {r['neg_rate']:5.0%}   z={r['z']}")

    # --- 3. terms file for prefilter.py: strong, not-too-rare terms ---
    top = [r for r in rows if r["z"] >= 3 and r["pos_rate"] >= 0.25][:80]
    with open(os.path.join(ROOT, "data", "terms_derived.txt"), "w") as f:
        f.write("# Derived by src/derive_terms.py from Suva's Q4-2025/Q1-2026 list vs other chamber 8/9 rulings\n")
        for r in top:
            term = r["term"]
            if term.startswith("[law] "):
                f.write(f"re:\\bArt\\.[^.]{{0,25}}\\b{re.escape(term[6:])}\\b   # {r['lang']} z={r['z']}\n")
            elif term.startswith("[insurer]"):
                f.write("re:\\b(Suva|SUVA|CNA|INSAI)\\b   # insurer named\n")
            else:
                f.write(f"{term}   # {r['lang']} z={r['z']} {r['pos_rate']:.0%} vs {r['neg_rate']:.0%}\n")
    print(f"\n{len(rows)} terms scored -> {out}; {len(top)} written to data/terms_derived.txt")


if __name__ == "__main__":
    main()
