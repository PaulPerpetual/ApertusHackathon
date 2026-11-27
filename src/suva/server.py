"""FastAPI backend for the triage UI. Serves the static frontend and a small JSON API."""
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, llm

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Suva judgement triage")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

JOBS = {}  # docket -> {"status": "running"|"done"|"error", "message": str}


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
    editor: str | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    return {"model": llm.model_name(), "mock": config.USE_MOCK_LLM,
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
