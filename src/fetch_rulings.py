"""Fetch the full Federal Supreme Court rulings for the cases Suva has summarised.

bger.ch blocks scripted access (Incapsula), so this uses entscheidsuche.ch, the public
open-data mirror of Swiss court decisions. Each ruling is stored as
  data/bger/<8C_178_2025>.html  (original ruling text, as published)
  data/bger/<8C_178_2025>.json  (entscheidsuche metadata: language, date, header, source URL)
and data/bger/index.csv lists every case with where it came from (summary file / spreadsheet).

Decision dates are needed to build the file name. They come from the summary titles
("Arrêt du TC 8C_178/2025 du 9 juillet 2025") and the spreadsheet's SharePoint URLs
("BGer-Urteil-8C_464-2025-vom-25.-Februar-2026"). Cases without a date fall back to
the entscheidsuche search API.

    python src/fetch_rulings.py
"""
import csv
import glob
import html
import json
import os
import re
import time
import urllib.error
import urllib.request

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JUDG = os.path.join(ROOT, "judgements")
OUT = os.path.join(ROOT, "data", "bger")
DOCS = "https://entscheidsuche.ch/docs/CH_BGer/"
UA = {"User-Agent": "lex-aperta-hackapertus/0.1"}

MONTHS = {
    # de
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5, "juni": 6, "juli": 7,
    "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    # fr
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "juin": 6, "juillet": 7,
    "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}
CASE = re.compile(r"(\d[A-Z])[_ /.-](\d+)[_/.-](\d{4})")
DATE = re.compile(r"(\d{1,2})\.?\s*(?:er\s+)?([A-Za-zÀ-ÿ]+)\s+(\d{4})")


def norm(m):
    return f"{m[1]}_{m[2]}/{m[3]}"


def parse_date(text):
    for d, mon, y in DATE.findall(text.replace("-", " ").replace("1er", "1")):
        mo = MONTHS.get(mon.lower())
        if mo:
            return f"{int(y):04d}-{mo:02d}-{int(d):02d}"
    return None


def text_of(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", raw))).strip()


def collect():
    cases = {}  # case -> {"date":..., "sources": set()}

    def add(case, date, src):
        c = cases.setdefault(case, {"date": None, "sources": set()})
        c["date"] = c["date"] or date
        c["sources"].add(src)

    for f in sorted(glob.glob(os.path.join(JUDG, "Export_*.html"))):
        t = text_of(f)
        m = CASE.search(t) or CASE.search(os.path.basename(f))
        if m:
            head = t[: t.find("Text DE")] if "Text DE" in t else t[:300]
            add(norm(m), parse_date(head), "summary:" + os.path.basename(f))

    ws = openpyxl.load_workbook(os.path.join(JUDG, "BG_Urteile_2025_Q4_2026_Q1.xlsx")).active
    for row in ws.iter_rows(min_row=2):
        title = row[1].value
        if not title:
            continue
        link = row[3].hyperlink.target if row[3].hyperlink else ""
        m = CASE.search(title) or CASE.search(link)
        if not m:  # e.g. "BGer-Urteil 458/2025 ..." without chamber: accident-law chamber 8C
            bare = re.search(r"BGer-Urteil\s+(\d+)/(\d{4})", title)
            m = ("", "8C", bare[1], bare[2]) if bare else None
        if not m:
            print(f"  skip spreadsheet row (no federal case number): {title}")
            continue
        add(norm(m), parse_date(title) or parse_date(link.replace("-", " ").replace(".", " ")),
            f"spreadsheet:{row[0].value}")
    return cases


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def search_date(case):
    """Fall back to an id-prefix search on entscheidsuche (see crawl_period.find_case)."""
    from crawl_period import find_case
    try:
        hits = find_case(case)
    except Exception as e:  # noqa: BLE001
        print(f"  search failed for {case}: {e}")
        return None
    return hits[-1] if hits else None


def stem(case, date):
    """8C_178/2025 + 2025-07-09 -> CH_BGer_008_8C-178-2025_2025-07-09 (008 = chamber 8)."""
    chamber, letter, n, y = re.match(r"(\d)([A-Z])_(\d+)/(\d{4})", case).groups()
    return f"CH_BGer_{int(chamber):03d}_{chamber}{letter}-{n}-{y}_{date}"


def main():
    os.makedirs(OUT, exist_ok=True)
    cases = collect()
    print(f"{len(cases)} federal cases referenced")
    rows = []
    for case in sorted(cases):
        info = cases[case]
        safe = case.replace("/", "_")
        status, doc_id = "", None
        if info["date"]:
            doc_id = stem(case, info["date"])
        if os.path.exists(os.path.join(OUT, safe + ".html")):
            status = "cached"
        else:
            for attempt in (doc_id, None):
                if attempt is None:
                    attempt = search_date(case)
                    if not attempt or attempt == doc_id:
                        break
                    doc_id = attempt
                try:
                    meta = get(DOCS + attempt + ".json")
                    body = get(DOCS + attempt + ".html")
                except urllib.error.HTTPError as e:
                    status = f"http {e.code}"
                    continue
                open(os.path.join(OUT, safe + ".json"), "wb").write(meta)
                open(os.path.join(OUT, safe + ".html"), "wb").write(body)
                status = "ok"
                break
            time.sleep(0.5)
        lang = ""
        if os.path.exists(os.path.join(OUT, safe + ".json")):
            lang = json.load(open(os.path.join(OUT, safe + ".json"))).get("Sprache", "")
        rows.append({"case": case, "decision_date": info["date"] or "", "language": lang, "status": status,
                     "entscheidsuche_id": doc_id or "", "sources": ";".join(sorted(info["sources"]))})
        print(f"  {case:14} {info['date'] or '?':10} {lang:2} {status}")
    with open(os.path.join(OUT, "index.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    ok = sum(r["status"] in ("ok", "cached") for r in rows)
    print(f"\n{ok}/{len(rows)} rulings fetched -> {OUT}")


if __name__ == "__main__":
    main()
