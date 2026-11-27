"""Fetch newly published Federal Supreme Court judgements from bger.ch (AZA database).

bger.ch publishes a daily "news" list of new decisions. For each publication day we read
the list, keep every docket link, and fetch the full text of each judgement. Raw HTML is
cached under data/cache/ so reruns (and demos) do not hit the site again.

The parser is deliberately tolerant: it looks for any link carrying an `aza://` docid.
"""
import hashlib
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


def fetch_single(docket_or_url, log=print):
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
