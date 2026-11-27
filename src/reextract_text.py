"""Re-extract judgements.text (and fill judgements.html) from the downloaded originals.

Needed after the _html_text fix (inline links no longer break sentences). Consideration numbering is
checked to stay identical, so summary references and jump links remain valid.

    python src/reextract_text.py data/aprjun.sqlite data/period/2026-04-01_2026-06-30
"""
import glob
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import erwaegungen, scraper  # noqa: E402


def main(db, folder):
    con = sqlite3.connect(db, timeout=30)
    rulings = os.path.join(folder, "rulings") if os.path.isdir(os.path.join(folder, "rulings")) else folder
    files = {}
    for f in glob.glob(os.path.join(rulings, "*.html")):
        key = os.path.basename(f)  # CH_BGer_008_8C-17-2026_2026-06-29.html
        parts = key.split("_")
        if len(parts) < 4:
            continue
        docket = parts[3].replace("-", "_", 1).replace("-", "/", 1)
        if docket not in files or os.path.getsize(f) > os.path.getsize(files[docket]):
            files[docket] = f
    n = changed_nums = 0
    for docket, old in con.execute("SELECT docket, text FROM judgements").fetchall():
        f = files.get(docket)
        if not f:
            continue
        raw = open(f, encoding="utf-8", errors="ignore").read()
        new = scraper._html_text(raw)
        if erwaegungen.numbers(new) != erwaegungen.numbers(old or ""):
            changed_nums += 1
        con.execute("UPDATE judgements SET text=?, html=? WHERE docket=?", (new, scraper._html_clean(raw), docket))
        n += 1
    con.commit()
    print(f"{n} judgements re-extracted; consideration numbering changed for {changed_nums}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
