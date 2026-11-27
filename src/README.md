# Suva Urteilsradar (source)

Pipeline and UI for finding and summarising Federal Supreme Court judgements relevant to Suva.

```
entscheidsuche.ch ──crawl_period.py──▶ suva import ──▶ SQLite ──prefilter──▶ Apertus triage (score, title, reasons, tags)
                                   └─▶ score ≥ threshold ──▶ Apertus: key considerations ──▶ DE summary + FR summary
FastAPI ◀── UI: ranked cards · DE/FR switch · drag-and-drop / typed score overrides · side panel · edit history
```

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env          # add your Keera gateway key (LLM_API_KEY)
cd src
python -m suva demo           # optional: 54 Suva example summaries as demo cards, no bger.ch needed
python crawl_period.py --from 2025-10-01 --to 2026-03-31          # crawl via entscheidsuche.ch (bger.ch blocks scripts)
python -m suva import ../data/period/2025-10-01_2026-03-31 --divisions 8C,9C,4A   # triage + summarise
python -m suva eval           # hits / recall of the ranking against the Suva Excel list
python -m suva serve          # http://127.0.0.1:8000
```

Without `LLM_BASE_URL` everything runs against a labelled mock model, so the UI can be developed offline.
Other commands: `triage [--all]`, `add 8C_145/2025` (fetches via entscheidsuche.ch), `scrape` (direct bger.ch fallback).

Docker: `docker build -t suva . && docker run -p 8000:8000 --env-file .env suva`

## Modules (`src/suva/`)

| File | Role |
| --- | --- |
| `scraper.py` | loads the entscheidsuche.ch crawl (`load_crawled`), single-case fetch, direct bger.ch fallback |
| `examples.py` | parses the human Suva summaries (`judgements/*.html`) and the Excel ground truth |
| `triage.py` | keyword/division prefilter, then Apertus relevance score + DE/FR explanation + tags (JSON) |
| `summarize.py` | extract key considerations (with Erw. numbers), then write DE and FR separately, few-shot with the most similar Suva examples and a DE↔FR glossary |
| `pipeline.py` | glue; never shows the model Suva's own summary of the same judgement |
| `db.py` | SQLite schema: judgements, assessments (AI score + human override), summaries (AI text + edited text), edit log |
| `server.py`, `static/` | FastAPI + plain HTML/JS UI, no build step |

Editors are identified by a name typed once and remembered in the browser (no accounts).

## Deploy on a server (Docker)

```bash
git clone https://github.com/PaulPerpetual/ApertusHackathon.git && cd ApertusHackathon
cp .env.example .env    # LLM_API_KEY=..., and for a public URL also DEMO_PASSWORD=...
docker build -t suva .
docker run -d --name suva --restart unless-stopped -p 127.0.0.1:8000:8000 \
  --env-file .env -v "$PWD/data:/app/data" suva
# load data once (inside the container, same database volume):
docker exec suva python -m suva demo          # or: python -m suva import ../data/period/<from>_<to>
```

Put a reverse proxy with HTTPS in front, e.g. Caddy: `suva.example.ch { reverse_proxy 127.0.0.1:8000 }`.

| Variable | Effect |
| --- | --- |
| `DEMO_PASSWORD` (+ `DEMO_USER`, default `suva`) | HTTP basic auth on every page and API call |
| `READ_ONLY=1` | disables edits and on-demand summaries (public showcase) |

**Azure:** the same image runs on Azure Container Apps / App Service (region Switzerland North);
mount an Azure Files share at `/app/data` for the database and point `LLM_BASE_URL` at an Apertus
endpoint (e.g. vLLM on AKS / GPU VM, or a managed online endpoint).

## Knowledge base

The **Bibliothek / Bibliothèque** tab searches every summary we hold: AI summaries, human-edited ones and
Suva's own 54 example summaries. Filter by origin (Suva / AI / edited) and by tag; every term must match.
