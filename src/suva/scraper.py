"""Load Federal Supreme Court judgements.

Primary source: the entscheidsuche.ch crawl made by src/crawl_period.py / src/fetch_rulings.py
(bger.ch blocks scripted access). `load_crawled()` reads that output; `fetch_single()` uses
crawl_period to fetch one case on demand. The direct bger.ch AZA scraper below is kept as a fallback.

bger.ch publishes a daily "news" list of new decisions. For each publication day we read
the list, keep every docket link, and fetch the full text of each judgement. Raw HTML is
cached under data/cache/ so reruns (and demos) do not hit the site again.

The parser is deliberately tolerant: it looks for any link carrying an `aza://` docid.
"""
import hashlib
from pathlib import Path
import re
import time
from datetime import date, timedelta
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup

from . import config

BASE = "https://www.bger.ch/ext/eurospider/live/de/php/aza/http"
NEWS_URL = BASE + "/index_aza.php?date={d}&lang=de&mode=news"
DOC_URL = BASE + "/index.php?highlight_docid=aza%3A%2F%2F{docid}&lang=de&type=show_document"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HackApertus-Suva-research/0.1)"}
DOCID_RE = re.compile(r"aza://(\d{2}-\d{2}-\d{4})-(\d{1,2}[A-Z])_(\d{1,4})-(\d{4})")
POLITE_DELAY = 1.0  # seconds between requests


def _get(url, client):
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = config.CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".html")
    if key.exists():
        return key.read_text(encoding="utf-8")
    r = client.get(url, headers=HEADERS, timeout=60, follow_redirects=True)
    r.raise_for_status()
    key.write_text(r.text, encoding="utf-8")
    time.sleep(POLITE_DELAY)
    return r.text


def list_publications(day, client):
    """Return [{docid, docket, decision_date, subject}] published on `day`."""
    page = _get(NEWS_URL.format(d=day.strftime("%Y%m%d")), client)
    soup = BeautifulSoup(page, "html.parser")
    found = {}
    for a in soup.find_all("a", href=True):
        m = DOCID_RE.search(unquote(a["href"]))
        if not m:
            continue
        ddate, div, num, year = m.groups()
        docid = f"{ddate}-{div}_{num}-{year}"
        row = a.find_parent("tr")
        subject = ""
        if row:
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            subject = " · ".join(c for c in cells if c and docid not in c and f"{div}_{num}/{year}" not in c)
        d, mth, y = ddate.split("-")
        found[docid] = {
            "docid": docid,
            "docket": f"{div}_{num}/{year}",
            "division": div,
            "decision_date": f"{y}-{mth}-{d}",
            "publication_date": day.isoformat(),
            "subject": re.sub(r"\s+", " ", subject)[:300],
        }
    return list(found.values())


def fetch_text(docid, client):
    page = _get(DOC_URL.format(docid=docid), client)
    soup = BeautifulSoup(page, "html.parser")
    node = (soup.find(id="highlight_content") or soup.find("div", class_="content")
            or soup.find("div", id="content") or soup.body or soup)
    for t in node.find_all(["script", "style", "nav"]):
        t.decompose()
    text = node.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def detect_language(text):
    t = " " + text[:5000].lower() + " "
    scores = {
        "de": sum(t.count(w) for w in (" der ", " die ", " und ", " das ", " nicht ")),
        "fr": sum(t.count(w) for w in (" le ", " la ", " les ", " des ", " et ")),
        "it": sum(t.count(w) for w in (" il ", " della ", " che ", " del ", " non ")),
    }
    return max(scores, key=scores.get)


def scrape(days=92, end=None, divisions=None, with_text=True, log=print):
    """Yield judgement dicts for publications in the last `days` days.

    divisions: optional set like {"8C", "9C"} to only fetch full text for those.
    """
    end = end or date.today()
    with httpx.Client() as client:
        for i in range(days):
            day = end - timedelta(days=i)
            if day.weekday() >= 5:
                continue
            try:
                pubs = list_publications(day, client)
            except httpx.HTTPError as e:
                log(f"{day}: list failed ({e})")
                continue
            log(f"{day}: {len(pubs)} publications")
            for p in pubs:
                p["url"] = DOC_URL.format(docid=p["docid"])
                if with_text and (not divisions or p["division"] in divisions):
                    try:
                        p["text"] = fetch_text(p["docid"], client)
                        p["language"] = detect_language(p["text"])
                    except httpx.HTTPError as e:
                        log(f"  {p['docket']}: text failed ({e})")
                yield p


SUBJECT_RE = re.compile(r"\b(Gegenstand|Objet|Oggetto)\s+(.{0,250}?)(Beschwerde gegen|recours contre|ricorso contro|$)")


def _html_text(raw):
    soup = BeautifulSoup(raw, "html.parser")
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))


_KEEP = {"p", "div", "span", "br", "b", "strong", "i", "em", "u", "sup", "sub", "table", "thead", "tbody", "tr", "td", "th",
         "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "blockquote", "pre", "hr"}


def _html_clean(raw):
    """The ruling's own formatting, safe to show inside the app: whitelisted tags, no attributes
    (except http(s) links), no scripts, styles, forms or images."""
    soup = BeautifulSoup(raw, "html.parser")
    for t in soup.find_all(["script", "style", "head", "link", "meta", "form", "input", "button", "img", "iframe", "object", "svg"]):
        t.decompose()
    root = soup.body or soup
    for t in root.find_all(True):
        if t.name not in _KEEP:
            t.unwrap()
            continue
        href = t.get("href", "") if t.name == "a" else ""
        t.attrs = {}
        if href.startswith(("http://", "https://")):
            t.attrs = {"href": href, "target": "_blank", "rel": "noopener"}
    html = root.decode_contents() if root is not soup else str(root)
    return re.sub(r"\n{3,}", "\n\n", html).strip()


def load_crawled(folder, divisions=None):
    """Yield judgement dicts from a crawl folder (data/period/<from>_<to> or data/bger)."""
    import csv
    import json
    from pathlib import Path
    folder = Path(folder)
    rulings = folder / "rulings" if (folder / "rulings").is_dir() else folder
    for row in csv.DictReader(open(folder / "index.csv", encoding="utf-8")):
        docket = row.get("case") or row.get("docket")
        doc_id = row.get("id") or ""
        html_path = rulings / f"{doc_id}.html"
        if not html_path.exists():
            cands = list(rulings.glob(docket.replace("/", "_") + "*.html")) if docket else []
            if not cands:
                continue
            html_path = cands[0]
        div = row.get("chamber") or docket.split("_")[0]
        if divisions and div not in divisions:
            continue
        raw = html_path.read_text(encoding="utf-8", errors="ignore")
        text = _html_text(raw)
        m = SUBJECT_RE.search(re.sub(r"\s+", " ", text[:6000]))
        meta = {}
        jp = html_path.with_suffix(".json")
        if jp.exists():
            meta = json.loads(jp.read_text(encoding="utf-8"))
        yield {"docket": docket, "division": div, "decision_date": row.get("decision_date") or meta.get("Datum"),
               "language": (row.get("language") or meta.get("Sprache") or detect_language(text))[:2].lower(),
               "subject": m.group(2).strip() if m else "", "url": row.get("source_url") or None,
               "text": text, "html": _html_clean(raw), "source": "entscheidsuche"}


def fetch_single(docket_or_url, log=print):
    """Fetch one case via the entscheidsuche.ch helper (crawl_period.py); fall back to bger.ch."""
    try:
        import tempfile
        import crawl_period  # src/crawl_period.py, importable when running from src/
        docket = DOCID_RE.search(unquote(docket_or_url))
        docket = f"{docket.group(2)}_{docket.group(3)}/{docket.group(4)}" if docket else docket_or_url.strip()
        ids = crawl_period.find_case(docket)
        if ids:
            out = Path(tempfile.gettempdir())
            row, _ = crawl_period.download(ids[0], str(out))
            text = _html_text((out / f"{ids[0]}.html").read_text(encoding="utf-8", errors="ignore"))
            m = SUBJECT_RE.search(re.sub(r"\s+", " ", text[:6000]))
            return {"docket": row["case"], "division": row["chamber"], "decision_date": row["decision_date"],
                    "language": (row["language"] or detect_language(text))[:2].lower(), "url": row["source_url"],
                    "subject": m.group(2).strip() if m else "", "text": text, "source": "manual"}
    except ImportError:
        pass
    return _fetch_single_bger(docket_or_url, log)


def _fetch_single_bger(docket_or_url, log=print):
    """Fetch one judgement by docket ('8C_145/2025') or bger.ch URL. Needs the decision date
    for the docid, so for a bare docket we search the full-text index."""
    m = DOCID_RE.search(unquote(docket_or_url))
    with httpx.Client() as client:
        if not m:
            q = docket_or_url.strip().replace("_", " ")
            search = (BASE + "/index.php?lang=de&type=simple_query&query_words=" + httpx.QueryParams({"q": q})["q"]
                      + "&top_subcollection_aza=all")
            page = _get(search, client)
            m = DOCID_RE.search(unquote(page))
            if not m:
                raise ValueError(f"judgement {docket_or_url} not found on bger.ch")
        ddate, div, num, year = m.groups()
        docid = f"{ddate}-{div}_{num}-{year}"
        d, mth, y = ddate.split("-")
        text = fetch_text(docid, client)
        return {"docket": f"{div}_{num}/{year}", "division": div, "decision_date": f"{y}-{mth}-{d}",
                "url": DOC_URL.format(docid=docid), "text": text, "language": detect_language(text),
                "source": "manual"}
