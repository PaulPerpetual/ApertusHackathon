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

## Hosted API (live) ✅

**Base URL: `https://api.robotross.art/lex`** (all paths below go after it: `…/lex/api/judgements`).

| | |
|---|---|
| Troubleshooting page | <https://api.robotross.art/lex/debug>: status, data counts, key test, raw GET |
| Server-hosted UI (fallback) | <https://api.robotross.art/lex/>: the same UI, served by FastAPI |
| Server | team droplet (DigitalOcean **Frankfurt**), systemd service `lex-aperta`, Caddy TLS. Demo host only, not the sovereign deployment (that's the Dockerfile) |
| Data right now | 637 rulings: Suva's 54 example summaries + 583 April–June rulings scored by the **mock** model. Real Apertus results replace it tonight |
| Deploy | `deploy/robotsales.sh [--db data/suva.sqlite]` (Miguel) |

### Security model

- **Reads are public.** No key needed for any `GET`. The data is public court rulings plus our summaries.
- **Writes need a personal editor key**, sent as header **`X-Lex-Key: <key>`** on every `PUT`, `DELETE` and `POST`.
  Without it the API answers `401 {"detail": "editor key required (X-Lex-Key header)"}`.
  - One key per person (`miguel`, `paul`). The server stores only SHA-256 hashes. The key's owner is
    recorded as the editor in the edit log, so the `editor` field in the body can't be spoofed
    (it is still accepted, for local mode).
  - **Keys are never committed and never sent over GitHub** (this repo is public). Miguel passes them on
    directly. A key can be revoked or replaced server-side without a code change.
- **CORS:** only `https://paulperpetual.github.io` may call the API from a browser. Preflight needs no key.
- **Apertus key** exists only in the server's `/opt/lex-aperta/.env` (0600) and Miguel's local `.env`.
  The browser never sees it. `POST /api/judgements` (summarise another ruling) runs Apertus *on the server*,
  limited to 2 concurrent jobs and to docket numbers like `8C_123/2026`.
- `GET /api/status` now also returns `editor_key_required: true|false`.

### UI status (Paul)

Already done (commit `839f49e`, `src/suva/static/app.js` → `api()`), verified in a browser
(282 of 637 cards at <https://api.robotross.art/lex/>):

- **API base:** calls go to `API_BASE + path`, with `API_BASE = window.LEX_API_BASE ?? <page path prefix>`.
  So the server-hosted UI works behind `/lex`, and locally at `/`.
- **Editor key:** writes send `X-Lex-Key` from `localStorage["lex.key"]`. On `401` the UI asks once
  (`window.prompt`), stores the key and retries.

Still open for Paul:

1. **GitHub Pages → hosted API.** Pages still runs in STATIC mode (exported JSON, read-only). To use the
   live API from Pages, set `window.LEX_API_BASE = "https://api.robotross.art/lex"` in the Pages build
   (e.g. a small inline script in the assembled `index.html`) and turn STATIC off when it's set. CORS
   already allows `https://paulperpetual.github.io`.
2. Nicer key UX than `window.prompt` (a field next to "Name festlegen"), and show read-only when
   `GET /api/status` returns `editor_key_required: true` and no key is stored.
3. SharePoint look (see `STATUS.md`).

## Endpoints (live mode, from `src/suva/server.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/status` | – | `{model, mock, read_only, threshold, jobs}` |
| GET | `/api/kb?q=&tag=&kind=&lang=` | – | library search over all summaries (AI, edited, Suva examples) |
| GET | `/api/kb/example/{docket}` | – | one Suva example summary |
| GET | `/api/judgements` | – | list of cards (`db.list_cards`) ranked by effective score |
| GET | `/api/judgements/{slug}` | – | detail (`db.get_detail`): card + text, summaries, history |
| PUT | `/api/judgements/{slug}/score` | `{score: 0-100, editor}` | `{ok}`; logged in `edits` |
| PUT | `/api/judgements/{slug}/status` | `{status: "new"\|"done", editor}` | `{ok}`; team-wide "Erledigt" state, logged in `edits` (unread/read is per browser) |
| DELETE | `/api/judgements/{slug}/score` | `{editor}` | `{ok}`; reverts to AI score |
| PUT | `/api/judgements/{slug}/summary/{de\|fr}` | `{text, editor}` | `{ok}`; logged in `edits` |
| POST | `/api/judgements` | `{docket: "8C_123/2026", editor?}` | job `{status}`; fetch + triage + summarise |

`slug` = docket with `/` → `_` (`8C_145/2025` → `8C_145_2025`).

### Card fields the UI relies on (`db.list_cards`)

`slug, docket, status, status_by, status_at, decision_date, division, language, subject, url, source, ai_score,
score_override, override_by, title_de, title_fr, explanation_de, explanation_fr, tags, tags_fr (FR translation of tags, same order; [] for older rows),
suva_party, model, has_summary`. The effective score is `score_override ?? ai_score`.

### Pipeline additions proposed (Miguel; additive, no breaking change)

| Field | Where | Meaning |
|---|---|---|
| `areas` | card | `["accident" \| "invalidity" \| "daily_allowance"]` from the subject line |
| `procedural` | card | appeal dismissed without a decision on the merits; Suva rarely picks these (3/26) |
| `dataset` | card | `"period"` (Apr–Jun 2026, the triage target) \| `"examples"` (Suva's 82 reference rulings) |
| `expert_summaries` | detail | `{de, fr, author}` Suva's human summary, for side-by-side comparison on example rulings. **Implemented** (PR: citations + compare) |

## Runtime notes

- Python **≥ 3.9** (fixed in PR #2).
- LLM config via `.env` (never committed): `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`. See `docs/STATUS.md`.
