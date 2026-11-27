# Suva Urteilsradar (source)

Pipeline and UI for finding and summarising Federal Supreme Court judgements relevant to Suva.

```
bger.ch ──scraper──▶ SQLite ──prefilter──▶ Apertus triage (score, title, reasons, tags)
                                   └─▶ score ≥ threshold ──▶ Apertus: key considerations ──▶ DE summary + FR summary
FastAPI ◀── UI: ranked cards · DE/FR switch · drag-and-drop / typed score overrides · side panel · edit history
```

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env          # add your Keera gateway key (LLM_API_KEY)
cd src
python -m suva demo           # optional: 54 Suva example summaries as demo cards, no bger.ch needed
python -m suva run --days 92 --divisions 8C,9C,4A   # scrape bger.ch + triage + summarise
python -m suva eval           # hits / recall of the ranking against the Suva Excel list
python -m suva serve          # http://127.0.0.1:8000
```

Without `LLM_BASE_URL` everything runs against a labelled mock model, so the UI can be developed offline.
Other commands: `scrape` (no LLM), `triage [--all]`, `add 8C_145/2025`.

Docker: `docker build -t suva . && docker run -p 8000:8000 --env-file .env suva`

## Modules (`src/suva/`)

| File | Role |
| --- | --- |
| `scraper.py` | bger.ch AZA daily publication lists + full texts, cached in `data/cache/` |
| `examples.py` | parses the human Suva summaries (`judgements/*.html`) and the Excel ground truth |
| `triage.py` | keyword/division prefilter, then Apertus relevance score + DE/FR explanation + tags (JSON) |
| `summarize.py` | extract key considerations (with Erw. numbers), then write DE and FR separately, few-shot with the most similar Suva examples and a DE↔FR glossary |
| `pipeline.py` | glue; never shows the model Suva's own summary of the same judgement |
| `db.py` | SQLite schema: judgements, assessments (AI score + human override), summaries (AI text + edited text), edit log |
| `server.py`, `static/` | FastAPI + plain HTML/JS UI, no build step |

Editors are identified by a name typed once and remembered in the browser (no accounts).
