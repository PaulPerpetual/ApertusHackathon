"""Parse Suva's human-written example summaries (judgements/*.html) into structured records.

Each file holds: title, Text DE, Text FR, link to the judgement, author.
They serve as few-shot style examples and as reference for evaluation.
"""
import glob
import html as htmllib
import json
import re

from bs4 import BeautifulSoup

from . import config

DOCKET_RE = re.compile(r"\b(\d{1,2}[A-Z])[_ ](\d{1,4})/(\d{4})\b")


def _section(soup, heading):
    h = soup.find(lambda t: t.name == "h2" and t.get_text(strip=True).lower() == heading.lower())
    if not h:
        return ""
    parts = []
    for sib in h.find_next_siblings():
        if sib.name == "h2":
            break
        txt = sib.get_text(" ", strip=True)
        if txt:
            parts.append(re.sub(r"\s+", " ", htmllib.unescape(txt)))
    return "\n\n".join(parts)


def parse_file(path):
    soup = BeautifulSoup(open(path, encoding="utf-8", errors="ignore").read(), "html.parser")
    title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else ""
    m = DOCKET_RE.search(title) or DOCKET_RE.search(soup.get_text(" "))
    link = soup.find("a")
    return {
        "docket": f"{m.group(1)}_{m.group(2)}/{m.group(3)}" if m else None,
        "title": title,
        "de": _section(soup, "Text DE"),
        "fr": _section(soup, "Text FR"),
        "url": link["href"] if link and link.has_attr("href") else None,
        "author": _section(soup, "Autor"),
        "file": path.split("/")[-1],
    }


def load_examples(refresh=False):
    if config.EXAMPLES_JSON.exists() and not refresh:
        return json.loads(config.EXAMPLES_JSON.read_text(encoding="utf-8"))
    out = []
    for f in sorted(glob.glob(str(config.JUDGEMENTS_DIR / "*.html"))):
        ex = parse_file(f)
        if ex["docket"] and ex["de"] and ex["fr"]:
            out.append(ex)
    config.EXAMPLES_JSON.parent.mkdir(parents=True, exist_ok=True)
    config.EXAMPLES_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def load_ground_truth():
    """Dockets Suva summarised in 2025 Q4 / 2026 Q1 (the Excel list). Returns {docket: quarter}."""
    import openpyxl
    wb = openpyxl.load_workbook(config.GROUND_TRUTH_XLSX, read_only=True)
    out = {}
    for row in wb.active.iter_rows(min_row=2, values_only=True):
        quarter, title = row[0], str(row[1] or "")
        m = DOCKET_RE.search(title)
        if m:
            out[f"{m.group(1)}_{m.group(2)}/{m.group(3)}"] = quarter
    return out
