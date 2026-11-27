"""Keyword pre-filter: shortlist rulings that may matter to Suva before Apertus triage.

For each crawled ruling it extracts the chamber, language and subject line
("Gegenstand" / "Objet" / "Oggetto"), then counts term hits from a terms file.
A ruling is a CANDIDATE if its subject is in one of Suva's insurance areas, or if it
matches any term. Apertus does the real relevance scoring afterwards (step 2); this only
cuts ~2,000 rulings down to a pool worth sending to the model, so it must favour recall.

Terms file: one term per line, '#' comments allowed. A line can be a plain word
(case-insensitive, matched as a whole word) or 're:<regex>'. Suva's official list goes in
data/terms_suva.txt; until then the defaults below, taken from the 82 rulings Suva
summarised, are used.

    python src/prefilter.py data/period/2026-04-01_2026-06-30 [--terms data/terms_suva.txt]
    python src/prefilter.py data/bger --recall      # check recall on the summarised set
"""
import argparse
import csv
import glob
import html
import os
import re

# Subject areas of all 82 rulings Suva summarised (DE / FR / IT).
SUBJECT_AREAS = {
    "accident": r"unfallversicherung|assurance[- ]accidents|assicurazione (contro gli )?infortuni|\bUVG\b|\bLAA\b",
    "invalidity": r"invalidenversicherung|assurance[- ]invalidit|assicurazione (per l')?invalidit|\bIVG\b|\bLAI\b",
    "daily_allowance": r"taggeldversicherung|indemnités? journalières?|indennità giornalier",
}
DEFAULT_TERMS = [
    "Suva", "SUVA", "CNA", "INSAI", "Unfall", "accident", "infortunio", "UVG", "LAA", "UVV", "OLAA",
    "Kausalzusammenhang", "lien de causalité", "Berufskrankheit", "maladie professionnelle",
    "Integritätsentschädigung", "indemnité pour atteinte à l'intégrité", "Taggeld", "Invalidenrente",
    "rente d'invalidité", "Heilbehandlung", "versicherter Verdienst", "gain assuré", "Regress", "recours",
]
SUBJECT = re.compile(r"\b(Gegenstand|Objet|Oggetto)\s+(.{0,250}?)(Beschwerde gegen|recours contre|ricorso contro|$)")


def load_terms(path):
    if not path:
        return DEFAULT_TERMS
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def compile_term(t):
    if t.startswith("re:"):
        return re.compile(t[3:], re.I)
    # acronyms stay case-sensitive so "CNA"/"LAA" don't match ordinary words
    flags = 0 if t.isupper() and len(t) <= 5 else re.I
    return re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)", flags)


def plain(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    raw = re.sub(r"(?s)<(script|style).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", raw))).strip()


def analyse(path, terms):
    t = plain(path)
    m = SUBJECT.search(t[:6000])
    subject = (m.group(2).strip(" ,;") if m else "")[:200]
    areas = [a for a, p in SUBJECT_AREAS.items() if re.search(p, subject, re.I)]
    hits = {term: len(rx.findall(t)) for term, rx in terms}
    hits = {k: v for k, v in hits.items() if v}
    name = os.path.basename(path)[:-5]
    chamber = re.search(r"(\d[A-Z])[-_]", name)
    return {"file": name, "chamber": chamber.group(1) if chamber else "", "subject": subject,
            "areas": ";".join(areas), "term_hits": sum(hits.values()),
            "terms": ";".join(f"{k}:{v}" for k, v in sorted(hits.items(), key=lambda kv: -kv[1])[:8]),
            "candidate": bool(areas) or bool(hits), "chars": len(t)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--terms")
    ap.add_argument("--recall", action="store_true", help="dir holds known-relevant rulings; report misses")
    a = ap.parse_args()
    terms = [(t, compile_term(t)) for t in load_terms(a.terms)]
    files = sorted(glob.glob(os.path.join(a.dir, "rulings", "*.html")) or glob.glob(os.path.join(a.dir, "*.html")))
    rows = [analyse(f, terms) for f in files]
    rows.sort(key=lambda r: (not r["areas"], -r["term_hits"]))
    out = os.path.join(a.dir, "candidates.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    by_area = sum(bool(r["areas"]) for r in rows)
    print(f"{len(rows)} rulings | subject in Suva areas: {by_area} | candidates (area or term): "
          f"{sum(r['candidate'] for r in rows)} -> {out}")
    if a.recall:
        for r in rows:
            if not r["areas"]:
                print("  no area match:", r["file"], "|", r["subject"][:100])


if __name__ == "__main__":
    main()
