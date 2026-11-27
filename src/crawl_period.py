"""Crawl every Federal Supreme Court ruling decided in a date range.

Source: entscheidsuche.ch, the public open-data mirror of Swiss court decisions
(bger.ch itself blocks scripted access). For each ruling we store:
  data/period/<from>_<to>/rulings/<id>.html   original ruling as published
  data/period/<from>_<to>/rulings/<id>.json   metadata (language, date, case no., source URL)
  data/period/<from>_<to>/index.csv           one row per ruling
Re-running skips files already downloaded.

    python src/crawl_period.py --from 2026-04-01 --to 2026-06-30
    python src/crawl_period.py --case 8C_234/2025      # look up single cases (no date needed)
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH = "https://entscheidsuche.ch/_search.php"
DOCS = "https://entscheidsuche.ch/docs/CH_BGer/"
UA = {"User-Agent": "lex-aperta-hackapertus/0.1", "Content-Type": "application/json"}
ID = re.compile(r"CH_BGer_\d{3}_(\d[A-Z])-(\d+)-(\d{4})_(\d{4}-\d{2}-\d{2})")


def search(query, size=500, search_after=None):
    body = {"query": query, "size": size, "_source": ["id", "date"],
            "sort": [{"date": "asc"}, {"id": "asc"}], "track_total_hits": True}
    if search_after:
        body["search_after"] = search_after
    req = urllib.request.Request(SEARCH, data=json.dumps(body).encode(), headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))["hits"]


def list_ids(date_from, date_to):
    q = {"bool": {"filter": [{"term": {"hierarchy": "CH_BGer"}},
                             {"range": {"date": {"gte": date_from, "lte": date_to}}}]}}
    ids, after = [], None
    while True:
        hits = search(q, search_after=after)
        page = hits["hits"]
        if not after:
            print(f"{hits['total']['value']} rulings between {date_from} and {date_to}")
        if not page:
            return ids
        ids += [h["_id"] for h in page]
        after = page[-1]["sort"]


def find_case(case):
    """8C_234/2025 -> entscheidsuche id(s), via a wildcard on the document id."""
    chamber, letter, n, y = re.match(r"(\d)([A-Z])_(\d+)/(\d{4})", case).groups()
    pre = f"CH_BGer_{int(chamber):03d}_{chamber}{letter}-{n}-{y}_"
    return [h["_id"] for h in search({"prefix": {"id": pre}}, size=10)["hits"]]


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            time.sleep(2 * (i + 1))
        except Exception:  # noqa: BLE001 - network hiccup, retry
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed after {tries} tries: {url}")


def download(doc_id, outdir):
    paths = {ext: os.path.join(outdir, f"{doc_id}.{ext}") for ext in ("json", "html")}
    fetched = False
    for ext, path in paths.items():
        if not os.path.exists(path):
            open(path, "wb").write(get(f"{DOCS}{doc_id}.{ext}"))
            fetched = True
    meta = json.load(open(paths["json"]))
    m = ID.match(doc_id)
    return {"id": doc_id, "case": f"{m[1]}_{m[2]}/{m[3]}", "chamber": m[1], "decision_date": m[4],
            "language": meta.get("Sprache", ""), "source_url": (meta.get("HTML") or {}).get("URL", "")}, fetched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--case", nargs="*", help="look up and print ids for single case numbers")
    a = ap.parse_args()

    if a.case:
        for c in a.case:
            print(c, find_case(c))
        return
    if not (a.date_from and a.date_to):
        sys.exit("need --from and --to (or --case)")

    base = os.path.join(ROOT, "data", "period", f"{a.date_from}_{a.date_to}")
    outdir = os.path.join(base, "rulings")
    os.makedirs(outdir, exist_ok=True)
    rows, failed = [], []
    ids = list_ids(a.date_from, a.date_to)
    for i, doc_id in enumerate(ids, 1):
        try:
            row, fetched = download(doc_id, outdir)
            rows.append(row)
            if fetched:
                time.sleep(0.2)
        except Exception as e:  # noqa: BLE001
            failed.append((doc_id, str(e)))
        if i % 100 == 0:
            print(f"  {i}/{len(ids)} ({len(failed)} failed)", flush=True)
    with open(os.path.join(base, "index.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"done: {len(rows)} rulings in {outdir}, {len(failed)} failed")
    for d, e in failed:
        print("  FAILED", d, e)


if __name__ == "__main__":
    main()
