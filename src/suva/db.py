"""SQLite storage. One file, no server: works on-prem, air-gapped and in a container.

Swap for Postgres (e.g. Azure Database for PostgreSQL) by replacing this module.
"""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS judgements (
    slug TEXT PRIMARY KEY,          -- 8C_145_2025
    docket TEXT NOT NULL,           -- 8C_145/2025
    decision_date TEXT,
    publication_date TEXT,
    division TEXT,
    language TEXT,
    subject TEXT,                   -- Rechtsgebiet / short title from the bger.ch list
    url TEXT,
    text TEXT,
    source TEXT DEFAULT 'bger',     -- bger | demo | manual
    fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS assessments (
    slug TEXT PRIMARY KEY REFERENCES judgements(slug),
    ai_score INTEGER,
    prefilter_score INTEGER,
    title_de TEXT, title_fr TEXT,
    explanation_de TEXT, explanation_fr TEXT,
    tags TEXT,                      -- JSON list
    suva_party INTEGER,
    model TEXT,
    created_at TEXT,
    score_override INTEGER,
    override_by TEXT,
    override_at TEXT
);
CREATE TABLE IF NOT EXISTS summaries (
    slug TEXT REFERENCES judgements(slug),
    lang TEXT,                      -- de | fr
    ai_text TEXT,
    text TEXT,                      -- current text (= ai_text until a human edits it)
    model TEXT,
    created_at TEXT,
    edited_by TEXT,
    edited_at TEXT,
    PRIMARY KEY (slug, lang)
);
CREATE TABLE IF NOT EXISTS edits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT,
    field TEXT,                     -- score | summary_de | summary_fr | revert_score
    old_value TEXT,
    new_value TEXT,
    editor TEXT,
    at TEXT
);
CREATE TABLE IF NOT EXISTS notes (          -- free-text team notes on a ruling
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT REFERENCES judgements(slug),
    text TEXT NOT NULL,
    editor TEXT,
    at TEXT
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(docket):
    return docket.replace("/", "_").replace(" ", "")


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH, timeout=30)  # parallel pipeline workers
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _migrate(con):
    """Additive columns for databases created before they existed."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(judgements)")}
    for name, ddl in (("status", "TEXT DEFAULT 'new'"), ("status_by", "TEXT"), ("status_at", "TEXT")):
        if name not in cols:
            con.execute(f"ALTER TABLE judgements ADD COLUMN {name} {ddl}")
    if "html" not in cols:
        con.execute("ALTER TABLE judgements ADD COLUMN html TEXT")  # cleaned original HTML (scraper._html_clean)
    acols = {r[1] for r in con.execute("PRAGMA table_info(assessments)")}
    # tags_fr: JSON list, same order as tags (DE). explanation_*_human: edited reasoning, kept apart from the
    # AI text so a re-triage never overwrites it.
    for name in ("tags_fr", "tags_human", "explanation_de_human", "explanation_fr_human", "explanation_edited_by", "explanation_edited_at"):
        if name not in acols:
            con.execute(f"ALTER TABLE assessments ADD COLUMN {name} TEXT")


def upsert_judgement(con, j):
    j = {"source": "bger", "fetched_at": now(), **j}
    j["slug"] = slugify(j["docket"])
    cols = ["slug", "docket", "decision_date", "publication_date", "division", "language",
            "subject", "url", "text", "html", "source", "fetched_at"]
    vals = [j.get(c) for c in cols]
    con.execute(
        f"INSERT INTO judgements ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
        f"ON CONFLICT(slug) DO UPDATE SET " + ",".join(f"{c}=COALESCE(excluded.{c},{c})" for c in cols[1:]),
        vals)
    return j["slug"]


def save_assessment(con, slug, a, model, prefilter_score):
    con.execute(
        """INSERT INTO assessments (slug, ai_score, prefilter_score, title_de, title_fr, explanation_de,
               explanation_fr, tags, tags_fr, suva_party, model, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(slug) DO UPDATE SET ai_score=excluded.ai_score, prefilter_score=excluded.prefilter_score,
               title_de=excluded.title_de, title_fr=excluded.title_fr, explanation_de=excluded.explanation_de,
               explanation_fr=excluded.explanation_fr, tags=excluded.tags, tags_fr=excluded.tags_fr, suva_party=excluded.suva_party,
               model=excluded.model, created_at=excluded.created_at""",
        (slug, a.get("score"), prefilter_score, a.get("title_de"), a.get("title_fr"), a.get("explanation_de"),
         a.get("explanation_fr"), json.dumps(a.get("tags") or [], ensure_ascii=False),
         json.dumps(a.get("tags_fr") or [], ensure_ascii=False), int(bool(a.get("suva_party"))), model, now()))


def save_summary(con, slug, lang, text, model):
    """Store an AI summary. Keeps a human-edited text if one exists."""
    con.execute(
        """INSERT INTO summaries (slug, lang, ai_text, text, model, created_at) VALUES (?,?,?,?,?,?)
           ON CONFLICT(slug, lang) DO UPDATE SET ai_text=excluded.ai_text, model=excluded.model,
               created_at=excluded.created_at,
               text=CASE WHEN summaries.edited_by IS NULL THEN excluded.text ELSE summaries.text END""",
        (slug, lang, text, text, model, now()))


def log_edit(con, slug, field, old, new, editor):
    con.execute("INSERT INTO edits (slug, field, old_value, new_value, editor, at) VALUES (?,?,?,?,?,?)",
                (slug, field, None if old is None else str(old), None if new is None else str(new), editor, now()))


def list_cards(con):
    rows = con.execute(
        """SELECT j.slug, j.docket, j.decision_date, j.publication_date, j.division, j.subject, j.url, j.source,
                  COALESCE(j.status, 'new') AS status, j.status_by, j.status_at,
                  a.ai_score, a.score_override, a.override_by, a.override_at, a.title_de, a.title_fr,
                  COALESCE(a.explanation_de_human, a.explanation_de) AS explanation_de,
                  COALESCE(a.explanation_fr_human, a.explanation_fr) AS explanation_fr, a.tags, a.tags_fr, a.tags_human, a.suva_party, a.model,
                  (SELECT COUNT(*) FROM summaries s WHERE s.slug=j.slug) AS n_summaries,
                  (SELECT COUNT(*) FROM notes n WHERE n.slug=j.slug) AS n_notes,
                  (SELECT e.editor FROM edits e WHERE e.slug=j.slug ORDER BY e.id DESC LIMIT 1) AS last_editor,
                  (SELECT e.at FROM edits e WHERE e.slug=j.slug ORDER BY e.id DESC LIMIT 1) AS last_edit_at
           FROM judgements j JOIN assessments a ON a.slug=j.slug""").fetchall()
    cards = []
    for r in rows:
        c = dict(r)
        _effective_tags(c)
        c["score"] = c["score_override"] if c["score_override"] is not None else c["ai_score"]
        cards.append(c)
    # ties: the most recently human-placed card first (so drag-and-drop between equal scores sticks)
    cards.sort(key=lambda c: c["docket"])
    cards.sort(key=lambda c: c["override_at"] or "", reverse=True)
    cards.sort(key=lambda c: -(c["score"] or 0))
    return cards


def _effective_tags(row, subject=None):
    """Tags shown and filtered on: a human's list if someone edited them, else the model's tags mapped onto
    the fixed Suva keyword list (suva/tags.py), plus what the court's own subject line ("Gegenstand", e.g.
    "Invalidenversicherung (Invalidenrente; Arbeitsunfähigkeit)") maps to. French labels come from the same list."""
    from . import tags as vocab
    ai = json.loads(row.get("tags") or "[]")
    human = json.loads(row["tags_human"]) if row.get("tags_human") else None
    row["tags_ai"] = ai
    row["tags_edited"] = human is not None
    subject = subject if subject is not None else row.get("subject")
    row["tags"] = human if human is not None else vocab.combine(ai, subject)
    row["tags_fr"] = vocab.french(row["tags"])
    row.pop("tags_human", None)
    return row


def get_detail(con, slug):
    j = con.execute("SELECT * FROM judgements WHERE slug=?", (slug,)).fetchone()
    if not j:
        return None
    d = dict(j)
    a = con.execute("SELECT * FROM assessments WHERE slug=?", (slug,)).fetchone()
    d["assessment"] = dict(a) if a else None
    if a:
        _effective_tags(d["assessment"], d.get("subject"))
        for lang in ("de", "fr"):  # effective reasoning = human edit if any; AI text stays available
            d["assessment"][f"explanation_{lang}_ai"] = a[f"explanation_{lang}"]
            if a[f"explanation_{lang}_human"] is not None:
                d["assessment"][f"explanation_{lang}"] = a[f"explanation_{lang}_human"]
    d["summaries"] = {r["lang"]: dict(r) for r in con.execute("SELECT * FROM summaries WHERE slug=?", (slug,))}
    d["notes"] = [dict(r) for r in con.execute("SELECT id, text, editor, at FROM notes WHERE slug=? ORDER BY id", (slug,))]
    d["history"] = [dict(r) for r in con.execute("SELECT * FROM edits WHERE slug=? ORDER BY id DESC", (slug,))]
    d["expert_summaries"] = _expert_summary(d["docket"])
    return d


_EXPERT = None


def _expert_summary(docket):
    """Suva's human summary for this docket, if it is one of the provided examples (docs/API.md)."""
    global _EXPERT
    if _EXPERT is None:
        from .examples import load_examples
        try:
            _EXPERT = {e["docket"]: e for e in load_examples()}
        except Exception:
            _EXPERT = {}
    e = _EXPERT.get(docket)
    return {"de": e["de"], "fr": e["fr"], "author": e.get("author")} if e else None
