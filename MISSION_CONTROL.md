# Lex Aperta — Mission Control

*Kanban board and project state. Updated by agents after each session.*

---

## Project Goal

Hack Apertus Zurich (27–28 Nov 2026), challenge partner **Suva**: find the Federal
Supreme Court (bger.ch) judgements from the last 3 months that matter for accident
insurance, score and explain their relevance, and write legally precise summaries
in German and French in Suva's house style. Show it all in a UI for legal experts.
Full brief: [`challenge_description.md`](challenge_description.md).

**Hard constraints**
- Model: Apertus v1.5 (8B or 70B) via the CSCS / Keera gateway. Configure it with the
  `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY` env vars, and never commit keys.
- Must be deployable sovereign: on-prem, air-gapped or Swiss cloud. Bonus if it moves easily to Azure.
- Keep the template layout: `README.md`, `technical_report.md`, `challenge_description.md`,
  `LICENSE`, `src/`. Don't rename or move them. The repo must be **public**.

**Deliverables:** public Git repo, technical report PDF (`TeamName_Report.pdf`, ≤6 pages),
demo video (≤2 min, linked in `technical_report.md`), pitch deck PDF (≤10 slides).

**How we're judged:** Suva's lawyers rate our top 10 summaries against their hold-out
summaries (quality score) and check our top 30 relevance-ranked judgements (hit score).

**Provided data (`judgements/`)**
- `Export_*.html` (55 files): **Suva's expert summaries**, one per judgement, each with a
  `Text DE` and a `Text FR` section. These are the style/structure references for step 3,
  not the court texts. Original judgements come from bger.ch.
- `BG_Urteile_2025_Q4_2026_Q1.xlsx` (60 rows): Suva's list of judgements it summarised in
  2025 Q4 – 2026 Q1 (number, date, SharePoint link that is internal to Suva and not reachable).
  Use it as the relevance ground truth for steps 1–2. About 31 rows overlap with the HTML
  summaries; the rest have no summary in the repo (possibly the hold-out set).

---

## Kanban

### Backlog (from the challenge steps; not yet ticketed)

| Step | Work |
|---|---|
| 1 | Ingest bger.ch publications from the last 3 months (sample set in `judgements/`, index in `judgements/BG_Urteile_2025_Q4_2026_Q1.xlsx`) |
| 2 | Relevance triage: score each judgement and explain why it was or wasn't selected (Suva / accident insurance) |
| 3 | DE + FR summaries in Suva's style. Write each language natively, not as a translation |
| 4 | UI: original document, sortable score, triage explanation, both summaries, summarise-on-demand |
| 5 | Bonus: searchable knowledge base and a better UX |

### In Progress / Todo

| Ticket | Title | Owner | Notes |
|---|---|---|---|

### Done

| Ticket | Title | Completed |
|---|---|---|
