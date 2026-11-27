# Lex Aperta — API / data contract

**Status: proposal from Miguel's side, building on PR #1 (Paul).** Comments welcome. Change it by PR.

## Split of work

| Area | Owner | Files |
|---|---|---|
| Crawl, filter, relevance (Apertus), summaries (Apertus), evaluation | **Miguel** | `src/crawl_period.py`, `src/fetch_rulings.py`, `src/prefilter.py`, `src/derive_terms.py`, `src/suva/triage.py`, `src/suva/summarize.py`, `src/suva/pipeline.py`, `src/suva/examples.py`, `src/suva/llm.py` |
| UI, API server, GitHub Pages site | **Paul** | `src/suva/server.py`, `src/suva/static/*` |
| Shared contract (change only by agreement) | both | `src/suva/db.py` (schema + `list_cards` / `get_detail`), this file |

**The rule:** the pipeline only *writes* the SQLite DB (`data/suva.sqlite`). The UI only
*reads* it through the endpoints below. `db.list_cards()` and `db.get_detail()` are the
contract: the pipeline may add columns and fields, but must not rename or remove any without
a heads-up and a bump of `schema_version`.

## Two run modes, one contract

The solution must run on **GitHub Pages**, which serves static files only. There's no Python,
no SQLite and no Apertus calls in the browser, because the key must stay secret. So the same data
is served two ways:

| | Live mode (`python -m suva serve`) | Static mode (GitHub Pages) |
|---|---|---|
| Data | FastAPI reads SQLite | `site/api/*.json`, exported from SQLite |
| Read | `GET /api/status`, `/api/judgements`, `/api/judgements/{slug}` | `api/status.json`, `api/judgements.json`, `api/judgements/{slug}.json` |
| Score override / summary edit | `PUT …/score`, `PUT …/summary/{lang}` | read-only (UI hides or disables edit controls) |
| Summarise another ruling | `POST /api/judgements` (background job) | link to a prefilled GitHub issue → GitHub Action runs the pipeline with the Apertus key from repo secrets, commits the new JSON, Pages redeploys |
| Where it runs | on-prem / air-gapped / Azure container (Dockerfile) | GitHub Pages (demo); same folder can be served by any intranet web server |

**Static files mirror the live responses byte for byte**, so the UI needs only one switch:

```js
// static mode when the page is served without the FastAPI backend
const STATIC = location.hostname.endsWith("github.io") || window.LEX_STATIC === true;
const url = (p) => STATIC ? p.replace(/^\/api\//, "api/") + ".json" : p;   // "/api/judgements" -> "api/judgements.json"
```

### Exporter (built in PR #3)

`python -m suva export site/` writes:

```
site/api/status.json                 = GET /api/status       (+ "static": true, "generated_at")
site/api/judgements.json             = GET /api/judgements    (db.list_cards)
site/api/judgements/<slug>.json      = GET /api/judgements/{slug}  (db.get_detail)
site/api/kb.json                     = all library entries (the browser filters them like GET /api/kb)
site/api/kb/example/<slug>.json      = GET /api/kb/example/{docket}
```

Run it from `src/` after the pipeline: `python -m suva export` (default target `../site`), then commit `site/api/`.

`.github/workflows/pages.yml` assembles the UI from `src/suva/static/` plus the committed `site/api/` and
publishes it on every push to `main`. Static mode turns on automatically on `*.github.io`, for `file://`, or
with `window.LEX_STATIC = true`. Pages must be enabled
once: repo **Settings → Pages → Source: GitHub Actions** (repo admin = Paul).

## Endpoints (live mode, from `src/suva/server.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/status` | – | `{model, mock, read_only, threshold, jobs}` |
| GET | `/api/kb?q=&tag=&kind=&lang=` | – | library search over all summaries (AI, edited, Suva examples) |
| GET | `/api/kb/example/{docket}` | – | one Suva example summary |
| GET | `/api/judgements` | – | list of cards (`db.list_cards`) ranked by effective score |
| GET | `/api/judgements/{slug}` | – | detail (`db.get_detail`): card + text, summaries, history |
| PUT | `/api/judgements/{slug}/score` | `{score: 0-100, editor}` | `{ok}`; logged in `edits` |
| DELETE | `/api/judgements/{slug}/score` | `{editor}` | `{ok}`; reverts to AI score |
| PUT | `/api/judgements/{slug}/summary/{de\|fr}` | `{text, editor}` | `{ok}`; logged in `edits` |
| POST | `/api/judgements` | `{docket: "8C_123/2026", editor?}` | job `{status}`; fetch + triage + summarise |

`slug` = docket with `/` → `_` (`8C_145/2025` → `8C_145_2025`).

### Card fields the UI relies on (`db.list_cards`)

`slug, docket, decision_date, division, language, subject, url, source, ai_score,
score_override, override_by, title_de, title_fr, explanation_de, explanation_fr, tags,
suva_party, model, has_summary`. The effective score is `score_override ?? ai_score`.

### Pipeline additions proposed (Miguel; additive, no breaking change)

| Field | Where | Meaning |
|---|---|---|
| `areas` | card | `["accident" \| "invalidity" \| "daily_allowance"]` from the subject line |
| `procedural` | card | appeal dismissed without a decision on the merits; Suva rarely picks these (3/26) |
| `dataset` | card | `"period"` (Apr–Jun 2026, the triage target) \| `"examples"` (Suva's 82 reference rulings) |
| `expert_summaries` | detail | `{de, fr}` Suva's human summary, for side-by-side comparison on example rulings |

## Runtime notes

- Python **≥ 3.9** (fixed in PR #2).
- LLM config via `.env` (never committed): `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`. See `docs/STATUS.md`.
