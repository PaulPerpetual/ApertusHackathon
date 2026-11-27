"""FastAPI backend for the triage UI. Serves the static frontend and a small JSON API."""
import base64
import hashlib
import json
import re
import secrets
import threading
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, examples, llm, tags

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Suva judgement triage")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}  # data files change on every pipeline run

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
    if config.EDITOR_KEYS and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        digest = hashlib.sha256(request.headers.get("x-lex-key", "").encode()).hexdigest()
        editor = next((n for d, n in config.EDITOR_KEYS.items() if secrets.compare_digest(d, digest)), None)
        if not editor:
            return Response('{"detail":"editor key required (X-Lex-Key header)"}', status_code=401,
                            media_type="application/json")
        request.state.editor = editor
    response = await call_next(request)
    # UI files: the browser must revalidate every time (cheap 304 via ETag), so a deploy shows up
    # on a normal reload instead of after Cmd+Shift+R.
    p = request.url.path
    if p.startswith("/static/") or p in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-cache"
    return response


def _editor(request: Request, claimed):
    """Editor of record: the key's owner when keys are enforced, else what the client sent."""
    return getattr(request.state, "editor", None) or claimed


if config.CORS_ORIGINS:
    # Registered after the guard, so it wraps it: preflight (OPTIONS) never needs a key,
    # and 401s still carry CORS headers so the browser can show the error.
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-Lex-Key"])


class ScoreIn(BaseModel):
    score: int = Field(ge=0, le=100)
    editor: str = Field(min_length=1, max_length=60)


class SummaryIn(BaseModel):
    text: str
    editor: str = Field(min_length=1, max_length=60)


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    editor: str = Field(min_length=1, max_length=60)


class TagsIn(BaseModel):
    tags: List[str] = Field(max_length=12)
    editor: str = Field(min_length=1, max_length=60)


class EditorIn(BaseModel):
    editor: str = Field(min_length=1, max_length=60)


class StatusIn(BaseModel):
    status: str = Field(pattern="^(new|done|rejected)$")
    editor: str = Field(min_length=1, max_length=60)


class AddIn(BaseModel):
    docket: str = Field(min_length=3, max_length=300)
    editor: Optional[str] = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/stats")
def stats_page():
    """Model statistics page: comparison, F2 curves, April-June overview (data: GET /api/stats)."""
    return FileResponse(STATIC / "stats.html")


@app.get("/api/stats")
def stats_json():
    """Precomputed by src/build_stats.py (data/stats.json, deployed with the DB)."""
    path = config.ROOT / "data" / "stats.json"
    if not path.exists():
        raise HTTPException(404, "stats not built yet")
    return FileResponse(path, media_type="application/json", headers=NO_CACHE)


@app.get("/compare")
def compare_page():
    """Compare runs of models / agents / versions (data/runs, built by src/runs.py)."""
    return FileResponse(STATIC / "compare.html")


@app.get("/api/runs")
def runs_index():
    path = config.ROOT / "data" / "runs" / "index.json"
    if not path.exists():
        raise HTTPException(404, "no runs yet")
    return FileResponse(path, media_type="application/json", headers=NO_CACHE)


@app.get("/api/runs/{dataset}/{run_id}")
def run_rows(dataset: str, run_id: str):
    if not re.fullmatch(r"[\w.-]{1,80}", dataset) or not re.fullmatch(r"[\w.-]{1,80}", run_id):
        raise HTTPException(400, "bad name")
    base = config.ROOT / "data" / "runs" / dataset
    name = "_dockets.json" if run_id == "_dockets" else f"{run_id}.jsonl"
    path = base / name
    if not path.exists():
        raise HTTPException(404, "unknown run")
    if name.endswith(".json"):
        return FileResponse(path, media_type="application/json", headers=NO_CACHE)
    meta, rows = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            (rows.append(o) if "docket" in o else meta.update(o))
    return {"meta": meta, "rows": rows}


@app.get("/examples")
def examples_page():
    """Suva's expert summaries vs ours on the same rulings (data: GET /api/examples-compare)."""
    return FileResponse(STATIC / "examples.html")


@app.get("/api/examples-compare")
def examples_compare():
    path = config.ROOT / "data" / "examples_compare.json"  # built by src/build_examples_compare.py
    if not path.exists():
        raise HTTPException(404, "not built yet")
    return FileResponse(path, media_type="application/json", headers=NO_CACHE)


@app.get("/hitlist")
def hitlist_page():
    """For Suva: ranked hit list (rank, ruling, normal/Grenzfall), live from the DB."""
    return FileResponse(STATIC / "hitlist.html")


@app.get("/api/hitlist")
def hitlist(date_from: str = "2026-04-01", date_to: str = "2026-06-30"):
    """Tier 1 + Grenzfall, minus 'Nicht relevant' (status rejected) and overrides < 60, plus overrides >= 60;
    ranked by effective score (Tier 1 60-99, Grenzfall 20-59, see src/finalize.py)."""
    with db.connect() as con:
        rows = con.execute("""SELECT j.docket, j.slug, j.decision_date, COALESCE(j.status, 'new') AS status, a.tier,
                   a.ai_score, a.score_override, COALESCE(a.score_override, a.ai_score) AS score, a.title_de, a.title_fr
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            WHERE j.decision_date BETWEEN ? AND ?""", (date_from, date_to)).fetchall()
    out = []
    for r in rows:
        on = r["tier"] in (1, 2)
        if r["score_override"] is not None:
            on = r["score_override"] >= 60
        if r["status"] == "rejected":
            on = False
        if on:
            out.append({"docket": r["docket"], "slug": r["slug"], "decision_date": r["decision_date"],
                        "category": "Grenzfall" if r["tier"] == 2 and r["score_override"] is None else "normal",
                        "score": r["score"], "title_de": r["title_de"], "title_fr": r["title_fr"],
                        "human": r["score_override"] is not None})
    out.sort(key=lambda x: (-(x["score"] or 0), x["decision_date"] or ""), reverse=False)
    for i, x in enumerate(out, 1):
        x["rank"] = i
    return {"from": date_from, "to": date_to, "count": len(out),
            "normal": sum(x["category"] == "normal" for x in out), "grenzfall": sum(x["category"] == "Grenzfall" for x in out),
            "items": out}


@app.get("/debug")
def debug_page():
    """Troubleshooting page for the hosted API (status, data counts, key test)."""
    return FileResponse(STATIC / "debug.html")


def _data_version():
    """Changes whenever the DB file changes (redeploy, any edit): the UI polls it to auto-refresh."""
    try:
        st = config.DB_PATH.stat()
        return f"{st.st_mtime_ns}-{st.st_size}"
    except OSError:
        return ""


@app.get("/api/status")
def status():
    return {"model": llm.model_name(), "mock": config.USE_MOCK_LLM, "read_only": config.READ_ONLY,
            "editor_key_required": bool(config.EDITOR_KEYS), "data_version": _data_version(),
            "threshold": config.RELEVANCE_SUMMARY_THRESHOLD, "jobs": JOBS, "tag_vocab": tags.vocab()}


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
def set_score(slug: str, body: ScoreIn, request: Request):
    body.editor = _editor(request, body.editor)
    with db.connect() as con:
        a = con.execute("SELECT ai_score, score_override FROM assessments WHERE slug=?", (slug,)).fetchone()
        if not a:
            raise HTTPException(404, "not found")
        old = a["score_override"] if a["score_override"] is not None else a["ai_score"]
        con.execute("UPDATE assessments SET score_override=?, override_by=?, override_at=? WHERE slug=?",
                    (body.score, body.editor, db.now(), slug))
        db.log_edit(con, slug, "score", old, body.score, body.editor)
    return {"ok": True}


@app.put("/api/judgements/{slug}/status")
def set_status(slug: str, body: StatusIn, request: Request):
    """Team-wide workflow state: 'done' moves a ruling to Erledigt, 'rejected' to
    Nicht relevant (taken off the list), 'new' puts it back. (Unread is per browser.)"""
    body.editor = _editor(request, body.editor)
    with db.connect() as con:
        j = con.execute("SELECT status FROM judgements WHERE slug=?", (slug,)).fetchone()
        if not j:
            raise HTTPException(404, "not found")
        con.execute("UPDATE judgements SET status=?, status_by=?, status_at=? WHERE slug=?",
                    (body.status, body.editor, db.now(), slug))
        db.log_edit(con, slug, "status", j["status"] or "new", body.status, body.editor)
    return {"ok": True}


@app.delete("/api/judgements/{slug}/score")
def revert_score(slug: str, body: EditorIn, request: Request):
    body.editor = _editor(request, body.editor)
    with db.connect() as con:
        a = con.execute("SELECT ai_score, score_override FROM assessments WHERE slug=?", (slug,)).fetchone()
        if not a:
            raise HTTPException(404, "not found")
        con.execute("UPDATE assessments SET score_override=NULL, override_by=NULL, override_at=NULL WHERE slug=?",
                    (slug,))
        db.log_edit(con, slug, "revert_score", a["score_override"], a["ai_score"], body.editor)
    return {"ok": True}


@app.put("/api/judgements/{slug}/summary/{lang}")
def set_summary(slug: str, lang: str, body: SummaryIn, request: Request):
    body.editor = _editor(request, body.editor)
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


@app.put("/api/judgements/{slug}/explanation/{lang}")
def set_explanation(slug: str, lang: str, body: SummaryIn, request: Request):
    """Edit the reasoning ("Begründung"). Stored beside the AI text, so re-running triage keeps the edit."""
    body.editor = _editor(request, body.editor)
    if lang not in ("de", "fr"):
        raise HTTPException(400, "lang must be de or fr")
    with db.connect() as con:
        a = con.execute(f"SELECT COALESCE(explanation_{lang}_human, explanation_{lang}) AS t FROM assessments WHERE slug=?",
                        (slug,)).fetchone()
        if not a:
            raise HTTPException(404, "not found")
        con.execute(f"UPDATE assessments SET explanation_{lang}_human=?, explanation_edited_by=?, explanation_edited_at=?"
                    " WHERE slug=?", (body.text, body.editor, db.now(), slug))
        db.log_edit(con, slug, f"explanation_{lang}", a["t"], body.text, body.editor)
    return {"ok": True}


@app.put("/api/judgements/{slug}/tags")
def set_tags(slug: str, body: TagsIn, request: Request):
    """Replace the keywords by hand (German labels; ones from the fixed list get their French label automatically)."""
    body.editor = _editor(request, body.editor)
    clean = []
    for t in body.tags:
        t = re.sub(r"\s+", " ", t.lstrip("#")).strip()[:40]
        if t and t not in clean:
            clean.append(t)
    with db.connect() as con:
        a = con.execute("SELECT tags, tags_human FROM assessments WHERE slug=?", (slug,)).fetchone()
        if not a:
            raise HTTPException(404, "not found")
        old = db._effective_tags(dict(a))["tags"]
        con.execute("UPDATE assessments SET tags_human=? WHERE slug=?", (json.dumps(clean, ensure_ascii=False), slug))
        db.log_edit(con, slug, "tags", ", ".join(old), ", ".join(clean), body.editor)
    return {"ok": True}


@app.post("/api/judgements/{slug}/notes")
def add_note(slug: str, body: NoteIn, request: Request):
    body.editor = _editor(request, body.editor)
    with db.connect() as con:
        if not con.execute("SELECT 1 FROM judgements WHERE slug=?", (slug,)).fetchone():
            raise HTTPException(404, "not found")
        cur = con.execute("INSERT INTO notes (slug, text, editor, at) VALUES (?,?,?,?)", (slug, body.text, body.editor, db.now()))
        db.log_edit(con, slug, "note", None, body.text[:200], body.editor)
    return {"ok": True, "id": cur.lastrowid}


@app.delete("/api/judgements/{slug}/notes/{note_id}")
def delete_note(slug: str, note_id: int, body: EditorIn, request: Request):
    body.editor = _editor(request, body.editor)
    with db.connect() as con:
        n = con.execute("SELECT text FROM notes WHERE id=? AND slug=?", (note_id, slug)).fetchone()
        if not n:
            raise HTTPException(404, "not found")
        con.execute("DELETE FROM notes WHERE id=?", (note_id,))
        db.log_edit(con, slug, "note_deleted", n["text"][:200], None, body.editor)
    return {"ok": True}


@app.post("/api/judgements")
def add_judgement(body: AddIn):
    key = body.docket.strip()
    if not re.fullmatch(r"\d{1,2}[A-Z]_\d{1,5}/\d{4}", key):
        raise HTTPException(400, "docket must look like 8C_123/2026")
    if JOBS.get(key, {}).get("status") == "running":
        return JOBS[key]
    if sum(j.get("status") == "running" for j in JOBS.values()) >= config.MAX_JOBS:
        raise HTTPException(429, "too many summaries running, try again in a minute")
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
