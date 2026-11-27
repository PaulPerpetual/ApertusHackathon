"""FastAPI backend for the triage UI. Serves the static frontend and a small JSON API."""
import base64
import re
import secrets
import threading
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, examples, llm

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Suva judgement triage")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

JOBS = {}  # docket -> {"status": "running"|"done"|"error", "message": str}


@app.middleware("http")
async def guard(request: Request, call_next):
    """Optional basic auth (DEMO_PASSWORD) and read-only mode (READ_ONLY)."""
    if config.DEMO_PASSWORD:
        ok = False
        h = request.headers.get("authorization", "")
        if h.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(h[6:]).decode().partition(":")
                ok = secrets.compare_digest(user, config.DEMO_USER) and secrets.compare_digest(pw, config.DEMO_PASSWORD)
            except Exception:
                ok = False
        if not ok:
            return Response("Authentication required", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Suva Urteilsradar"'})
    if config.READ_ONLY and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        return Response("Read-only demo", status_code=403)
    return await call_next(request)


class ScoreIn(BaseModel):
    score: int = Field(ge=0, le=100)
    editor: str = Field(min_length=1, max_length=60)


class SummaryIn(BaseModel):
    text: str
    editor: str = Field(min_length=1, max_length=60)


class EditorIn(BaseModel):
    editor: str = Field(min_length=1, max_length=60)


class AddIn(BaseModel):
    docket: str = Field(min_length=3, max_length=300)
    editor: Optional[str] = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    return {"model": llm.model_name(), "mock": config.USE_MOCK_LLM, "read_only": config.READ_ONLY,
            "threshold": config.RELEVANCE_SUMMARY_THRESHOLD, "jobs": JOBS}


@app.get("/api/judgements")
def judgements():
    with db.connect() as con:
        return db.list_cards(con)


@app.get("/api/judgements/{slug}")
def judgement(slug: str):
    with db.connect() as con:
        d = db.get_detail(con, slug)
    if not d:
        raise HTTPException(404, "not found")
    return d


@app.put("/api/judgements/{slug}/score")
def set_score(slug: str, body: ScoreIn):
    with db.connect() as con:
        a = con.execute("SELECT ai_score, score_override FROM assessments WHERE slug=?", (slug,)).fetchone()
        if not a:
            raise HTTPException(404, "not found")
        old = a["score_override"] if a["score_override"] is not None else a["ai_score"]
        con.execute("UPDATE assessments SET score_override=?, override_by=?, override_at=? WHERE slug=?",
                    (body.score, body.editor, db.now(), slug))
        db.log_edit(con, slug, "score", old, body.score, body.editor)
    return {"ok": True}


@app.delete("/api/judgements/{slug}/score")
def revert_score(slug: str, body: EditorIn):
    with db.connect() as con:
        a = con.execute("SELECT ai_score, score_override FROM assessments WHERE slug=?", (slug,)).fetchone()
        if not a:
            raise HTTPException(404, "not found")
        con.execute("UPDATE assessments SET score_override=NULL, override_by=NULL, override_at=NULL WHERE slug=?",
                    (slug,))
        db.log_edit(con, slug, "revert_score", a["score_override"], a["ai_score"], body.editor)
    return {"ok": True}


@app.put("/api/judgements/{slug}/summary/{lang}")
def set_summary(slug: str, lang: str, body: SummaryIn):
    if lang not in ("de", "fr"):
        raise HTTPException(400, "lang must be de or fr")
    with db.connect() as con:
        s = con.execute("SELECT text FROM summaries WHERE slug=? AND lang=?", (slug, lang)).fetchone()
        if s:
            con.execute("UPDATE summaries SET text=?, edited_by=?, edited_at=? WHERE slug=? AND lang=?",
                        (body.text, body.editor, db.now(), slug, lang))
        else:
            con.execute("INSERT INTO summaries (slug, lang, ai_text, text, model, created_at, edited_by, edited_at)"
                        " VALUES (?,?,NULL,?,NULL,?,?,?)", (slug, lang, body.text, db.now(), body.editor, db.now()))
        db.log_edit(con, slug, f"summary_{lang}", s["text"] if s else None, body.text, body.editor)
    return {"ok": True}


def _run_add(docket):
    from . import pipeline, scraper
    try:
        j = scraper.fetch_single(docket)
        slug = pipeline.process(j, force_summary=True, log=lambda *_: None)
        JOBS[docket] = {"status": "done", "slug": slug}
    except Exception as e:  # report to UI
        JOBS[docket] = {"status": "error", "message": str(e)[:300]}


@app.post("/api/judgements")
def add_judgement(body: AddIn):
    key = body.docket.strip()
    if JOBS.get(key, {}).get("status") == "running":
        return JOBS[key]
    JOBS[key] = {"status": "running"}
    threading.Thread(target=_run_add, args=(key,), daemon=True).start()
    return JOBS[key]


# ----------------------------------------------------------------------------- knowledge base
def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).lower()


def kb_entries():
    return _kb_entries()


def _kb_entries():
    """All summaries we know: pipeline output (AI or human-edited) plus Suva's own example summaries."""
    with db.connect() as con:
        cards = {c["slug"]: c for c in db.list_cards(con)}
        sums = {}
        for r in con.execute("SELECT slug, lang, text, model, edited_by FROM summaries"):
            sums.setdefault(r["slug"], {})[r["lang"]] = dict(r)
    out, seen = [], set()
    for slug, langs in sums.items():
        c = cards.get(slug)
        if not c:
            continue
        seen.add(c["docket"])
        any_s = langs.get("de") or langs.get("fr")
        kind = "edited" if any(v.get("edited_by") for v in langs.values()) else \
            ("suva" if any_s.get("model") == "suva-human-example" else "ai")
        out.append({"slug": slug, "docket": c["docket"], "date": c["decision_date"] or c["publication_date"],
                    "title_de": c["title_de"], "title_fr": c["title_fr"], "tags": c["tags"], "score": c["score"],
                    "de": (langs.get("de") or {}).get("text") or "", "fr": (langs.get("fr") or {}).get("text") or "",
                    "kind": kind, "in_radar": True})
    for ex in examples.load_examples():
        if ex["docket"] in seen:
            continue
        out.append({"slug": None, "docket": ex["docket"], "date": None, "title_de": ex["title"], "title_fr": ex["title"],
                    "tags": [], "score": None, "de": ex["de"], "fr": ex["fr"], "kind": "suva", "in_radar": False,
                    "url": ex.get("url"), "author": ex.get("author")})
    return out


def _snippet(text, terms, width=220):
    low = text.lower()
    pos = min([low.find(t) for t in terms if t in low] or [0])
    start = max(0, pos - width // 3)
    snip = text[start:start + width]
    return ("…" if start else "") + snip + ("…" if start + width < len(text) else "")


@app.get("/api/kb")
def knowledge_base(q: str = "", tag: str = "", kind: str = "", lang: str = "de", limit: int = 100):
    terms = [t for t in _norm(q).split(" ") if len(t) > 1]
    results = []
    for e in _kb_entries():
        if tag and tag.lower() not in [x.lower() for x in e["tags"]]:
            continue
        if kind and e["kind"] != kind:
            continue
        hay = _norm(" ".join([e["docket"], e["title_de"] or "", e["title_fr"] or "", e["de"], e["fr"], " ".join(e["tags"])]))
        if terms and not all(t in hay for t in terms):
            continue
        rank = sum(hay.count(t) for t in terms) + (5 if any(t in _norm(e["docket"]) for t in terms) else 0)
        body = e[lang] or e["de"] or e["fr"]
        results.append({**{k: v for k, v in e.items() if k not in ("de", "fr")},
                        "snippet": _snippet(body, terms) if terms else body[:220] + ("…" if len(body) > 220 else ""),
                        "rank": rank})
    results.sort(key=lambda r: (-r["rank"], r["date"] or "", r["docket"]), reverse=False)
    if not terms:
        results.sort(key=lambda r: r["date"] or "", reverse=True)
    tags = sorted({t for e in results for t in e["tags"]})
    return {"total": len(results), "results": results[:limit], "tags": tags}


@app.get("/api/kb/example/{docket:path}")
def kb_example(docket: str):
    for ex in examples.load_examples():
        if ex["docket"] == docket:
            return ex
    raise HTTPException(404, "not found")
