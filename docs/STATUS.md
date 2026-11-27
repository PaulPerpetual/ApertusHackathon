# Lex Aperta — status (Fri 27 Nov 2026, late afternoon)

For Paul (and Paul's AI): where Miguel's side stands, what we found, what we propose.
The API/data contract is in [`docs/API.md`](API.md).

## ▶ Latest (Fri ~16:00): what changed in the data, and what it means for the UI

**Pages:** UI <https://api.robotross.art/lex/> · stats `/lex/stats` · model comparison `/lex/compare` · troubleshooting `/lex/debug`.
Same data in the repo: `site/api/` (177 Apertus-scored rulings, refreshed now).

**Data changes (all additive, same fields):**
1. **Tags = controlled vocabulary** (`src/suva/hashtags.py`, 52 tags in 6 groups, DE + FR). Each card has at most 5:
   subject area (`UVG` / `IV` / `Taggeldversicherung`), 2–3 **deciding grounds** chosen by Apertus
   (e.g. `natürliche-Kausalität`, `Beweiswert-Gutachten`, `Rentenrevision`, `öffentliche-Verhandlung-EMRK`), and the
   outcome (`gutgeheissen` / `abgewiesen` / `Rückweisung-zur-Abklärung` …). **Stored without `#`** (your UI adds it),
   no Suva-party tag (your `suva_party` badge covers it); `tags_fr` is aligned 1:1. Fixes the "##" and doubled tags.
   *Optional UI idea:* the grouped vocabulary could drive a tag filter (we can expose it as `GET /api/hashtags`).
2. **`explanation_de` / `_fr` ("Begründung") rewritten:** starts with the concrete legal question
   ("Stabilisierung des Gesundheitszustands nach Art. 19 Abs. 1 UVG: …"), cites the deciding consideration
   "(E. 5.2)" / "(consid. 5.2)", ends with the meaning for Suva. Never starts with "Das Bundesgericht / Das Urteil".
3. **Summaries (all 77 on the hit list) regenerated:** every paragraph cites real considerations ("(E. 4.4)",
   "(consid. 4.4)"), so your citation links now work. Outcome is taken from the Dispositiv and machine-checked; anonymisation
   placeholders ("A.________") removed. Median 246 words (Suva style 120–300).
4. **`text` re-extracted** without broken lines around statute links (was "(\nart. 90 LTF\n)"), and **`html` filled**
   for every ruling (formatted original via your `_html_clean`), so the "Urteilstext" tab shows the formatted ruling.
   Fix is in `scraper._html_text` (inline tags unwrapped). Consideration numbering unchanged.
5. **Titles** re-done with your `python -m suva relabel` (run on the master DB, then deployed).
6. **`GET /api/status` has `data_version`**; the UI polls every 30 s and reloads when data changes (paused while
   editing). That's in `app.js`, at the end of `init()`. Please keep it if you restructure.

**Evaluation (labelled window Oct 2025 – Mar 2026, 58 Suva picks; Suva scores Recall + F2):**

| Run | Listed | Recall | Precision | **F2** |
|---|---|---|---|---|
| **Apertus v1 (production: main ≥ 60 + IV second pass ≥ 40)** | 101 | 84 % | 49 % | **0.736** |
| Apertus v2 "general rule vs individual case" (rejected) | 259 | 98 % | 22 % | 0.580 |
| Apertus v3 "ATSG rescue" for Codex-style misses (rejected) | 211 | 91 % | 25 % | 0.598 |
| Baseline: all subject-area candidates | 288 | 100 % | 20 % | 0.558 |

Codex (GPT-6, development reference only, blind) is better at telling a *general rule* from a *routine
application* (on 40 labelled rulings: F2 0.84 vs Apertus 0.78). Two attempts to teach Apertus that distinction
(v2, v3) made it say "yes" to almost everything, so **v1 stays**. All runs are on `/compare`.

**Recall pass (new, 27 Nov, not yet evaluated):** `src/suva/recall_pass.py` re-assesses every subject-area
candidate below the cutoff with (1) five-judge panel as leading-case signal, (2) 3 samples at temperature 0.7,
highest counts, (3) the 3 most similar rulings Suva did / did not summarise (tf-idf, leave-one-out), (4) Suva
summaries of IV / procedural / Taggeld rulings decided before the window as illustrations. Run and compare:

    python src/run_recall_pass.py data/eval_window.sqlite --before 2025-10-01
    python src/eval_f2.py data/eval_window.sqlite --variants        # cutoffs 60/50/40, with and without
    # if F2 improves: same for April-June, then finalize with the chosen cutoff
    python src/run_recall_pass.py data/aprjun.sqlite --ref-db data/eval_window.sqlite --before 2026-04-01
    python src/finalize.py data/aprjun.sqlite --from 2026-04-01 --to 2026-06-30 --recall-pass 60

**Submission artefacts:** hit list `data/submission/hitlist_2026-04-01_2026-06-30.txt` (77 rulings, Suva format);
summaries in the DB / `site/api/judgements/<slug>.json`.

**Not done / known gaps:** Codex flags 5 April–June rulings Apertus doesn't (all IV/ATSG procedure:
8C_580/2025, 9C_208/2025, 9C_230/2025, 9C_309/2025, 9C_368/2025). They're **not** on our list, because only Apertus may decide.
Server-side edits are overwritten when Miguel deploys a new DB. Tell him before you edit real content.

## ▶ Where the real data is (read this first, agents)

Real Apertus v1.5 70B results for **April – June 2026** (no mock data any more), three ways:

1. **In this repo (works from any sandbox, no network needed):**
   - `site/api/judgements.json`: the 177 rulings Apertus scored (cards: score, DE/FR title and explanation,
     hashtags, `has_summary`). Same shape as `GET /api/judgements`.
   - `site/api/judgements/<slug>.json`: detail per ruling (full text, assessment, summaries DE/FR,
     history), same shape as `GET /api/judgements/{slug}`. `slug` = `8C_137_2025`.
   - `site/api/kb.json`, `site/api/status.json`: library and status.
   - `data/submission/hitlist_2026-04-01_2026-06-30.txt`: **the hit list we submit** (77 rulings, Suva's format).
   - `data/stats.json`: model comparison and evaluation numbers (what `/stats` shows).
   This export is refreshed by Miguel after each pipeline run (`python -m suva export ../site` on a copy of the
   DB limited to Apertus-scored rulings). The other ~1,900 crawled rulings were rejected by the subject-area
   prefilter and aren't exported.
2. **Live API:** `https://api.robotross.art/lex/api/judgements` (public reads, see API.md). Cloud sandboxes may not
   reach this host; use option 1 there.
3. **Pages:** the `pages.yml` workflow publishes `site/` → read-only UI on GitHub Pages.

**Summaries are still being generated** (77 rulings, June first). The export and the live API are updated as they finish.

New fields in the data (additive, no breaking change):
- `tags` now start with **decision-criteria hashtags**, then Apertus' topic tags:
  `#Unfallversicherung` / `#Invalidenversicherung` / `#Taggeld`, `#materiell` / `#prozessual`, `#SuvaPartei`,
  `#IV-Grundsatz` (IV ruling promoted by the second Apertus pass), `#Trefferliste` (on the submitted hit list).
- An IV ruling promoted by the second pass has `score = 60` and its explanation ends with
  "— IV-Zweitprüfung (Apertus): <principle>".

Other pages: model statistics at <https://api.robotross.art/lex/stats>, troubleshooting at `/lex/debug`.

## How Suva scores us (from the challenge pitch, 27 Nov)

1. **Hit score: Recall and F2** on a plain list of case numbers ("8C_691/2024, 9C_612/2025, …") for rulings
   relevant in **Q2 2026**. F2 weighs recall 4× more than precision, so the cutoff is generous. Ranking order
   doesn't count for this score.
2. **Quality score: top 5 summaries**, checked against Suva's hold-out summaries **published in June 2026**.
   So June summaries matter most.

Current numbers on the labelled window (Oct 2025 – Mar 2026, 58 Suva picks): **F2 0.736, recall 84 %,
precision 49 %** (baseline "all subject-area candidates": F2 0.560). Details on `/stats`.

## Decisions

1. **Split:** Paul owns UI + API server + GitHub Pages; Miguel owns crawl, filter, relevance, summaries.
2. **Runs on GitHub Pages.** The UI must work as a static site. The pipeline exports the SQLite
   DB to static JSON that mirrors the live API (see API.md). The FastAPI server stays for
   on-prem / Docker / editing.
3. **Source of rulings: entscheidsuche.ch.** bger.ch blocks scripted access (Incapsula
   "Request unsuccessful"), from the Mac Mini as well as from the cloud. entscheidsuche.ch is the
   public open-data mirror with the same texts and a link back to bger.ch.
   `src/suva/scraper.py`'s direct bger.ch path will not work. Use `crawl_period.py`.

## Apertus access: working ✅

- Gateway `https://gateway.keera.ch/api/v1` (OpenAI-compatible), key from the CSCS/Keera perk.
  **The key is not in the repo.** Ask Miguel; put it in your local `.env`.
- Models: `apertus-v1-5-70b`, `apertus-v1-5-70b-thinking`, `apertus-v1-5-8b`, `apertus-v1-5-8b-thinking`.
  The non-thinking ones support tool calls.
- Tested: `apertus-v1-5-70b` answered a German UVG question correctly in ~4 s.

## Data we have (local, not committed: re-fetch with the scripts)

| Set | Size | Where |
|---|---|---|
| Suva's 82 reference rulings (55 expert summaries + 60-row Excel list) | 82 full texts | `data/bger/` via `src/fetch_rulings.py` |
| **Target: all federal rulings 1 Apr – 30 Jun 2026** | 2,095 rulings (1 non-social-law file failed) | `data/period/2026-04-01_2026-06-30/` |
| Labelled window: all chamber 8/9 rulings 1 Oct 2025 – 31 Mar 2026 | 733 distinct cases, 59 on Suva's list | `data/period/2025-10-01_2026-03-31_ch89/` |

Commands: `python src/crawl_period.py --from 2026-04-01 --to 2026-06-30`, `python src/fetch_rulings.py`.

## What we learned about Suva's selection (from the labelled window)

| Ruling type | Suva picked | Share |
|---|---|---|
| Accident insurance, decided on the merits | 40 / 66 | **61 %** |
| Accident insurance, procedural only (inadmissible, withdrawn, …) | 3 / 26 | 12 % |
| Invalidity insurance | 16 / 197 | 8 % |
| Anything else | 0 / 445 | 0 % |

- **The subject-line filter has 100 % recall** (82/82 reference rulings) and cuts April–June
  from 2,096 to **177 candidates** (117 invalidity, 56 accident, 4 daily allowance). `src/prefilter.py`.
- **"Suva" is not the signal.** Only 43/82 reference rulings name Suva/CNA/INSAI, and
  skipped accident rulings name Suva as often as picked ones (38 vs 39).
- **The invalidity picks are not keyword-separable.** The 16 picked vs 180 skipped look the
  same on every keyword we tested. This is where Apertus has to judge legal substance,
  using the expert summaries as context.
- **Derived term list:** `data/terms_derived.txt` / `.csv` (`src/derive_terms.py`), DE and FR,
  scored by how much more often a term appears in Suva's picks. There's no official Suva term list
  anywhere in the template repo or the HackApertus org (checked all commits and branches).

## Proposed pipeline changes (Miguel, next)

1. Prefilter in `triage.py`: use the subject-area rule (keeps recall at 100 %) instead of a pure keyword score.
2. Add the `procedural` flag and the 61 % / 12 % / 8 % base rates to the Apertus triage prompt.
3. Run `suva eval` on the labelled window (hits and recall vs Suva's list) before running April–June.
4. Run triage + summaries on the 177 April–June candidates with `apertus-v1-5-70b`.
5. Build `python -m suva export site/` for GitHub Pages (see API.md).

## Update (Fri 27 Nov, ~12:00): hosted API is live

- **`https://api.robotross.art/lex`**: Paul's FastAPI + SQLite, deployed on the team server. Pages can't host a DB.
  Details, security model and what the UI must change: [`API.md` → Hosted API](API.md#hosted-api-live-).
- **Keys:** writes need a personal `X-Lex-Key`. Miguel sends Paul his key directly, **not via GitHub**.
- **Troubleshooting:** <https://api.robotross.art/lex/debug>
- Data on the server is currently **mock-scored**. Real Apertus 70B results replace it tonight.

## UI look: make it feel like SharePoint (input from Miguel)

Suva's lawyers file their judgement summaries in **SharePoint** (the Excel list links to
`suvaprodcloud.sharepoint.com/sites/jlsm/SitePages/BGer-Urteil-…`). A UI that looks like their daily tool
lowers the barrier for the jury. Suggested Microsoft Fluent 2 / SharePoint conventions:

- **Font:** `"Segoe UI", "Segoe UI Web (West European)", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", sans-serif`
  (Segoe UI is on every Suva Windows machine; the fallbacks cover Mac and Linux).
- **Colours:** SharePoint theme blue `#0078D4` (links, primary buttons; hover `#106EBE`), neutrals
  `#323130` text, `#605E5C` secondary text, `#EDEBE9` borders, `#F3F2F1` page background, white cards.
- **Layout:** a top suite bar (thin dark bar with the app name), a site header with title and navigation, then a
  page that looks like a SharePoint **Site Page / news post**: title "BGer-Urteil 8C_123/2026 vom …",
  sections DE / FR, "Link zum Urteil", "Autor". This mirrors their existing pages, whose titles follow
  `BGer-Urteil <Nummer> vom <Datum>`.
- **Components:** Fluent-style command bar (New / Edit / Share), list view with column headers and sort arrows
  for the relevance list, details pane on the right.
- Keep it "SharePoint-like", not a copy: **no Microsoft or Suva logos** unless Suva gives us theirs to use.

## Asks for Paul

1. Static mode in `app.js` (one URL switch, read-only, see API.md) and a `pages.yml` workflow; enable Pages in repo settings.
2. "Summarise another ruling" on Pages: issue template + Action (can wait until the export works).
3. OK on the additive card fields in API.md (`areas`, `procedural`, `dataset`, `expert_summaries`)?

## Small findings from reviewing PR #1 (merged)

- Server needs Python ≥ 3.10 (`str | None` in `server.py` fails on the Mac's 3.9). Document it or add `from __future__ import annotations`.
- Cards imported from the crawl have an empty `subject`. The subject line ("Gegenstand/Objet") can be taken from the ruling text (`prefilter.SUBJECT`).
- Smoke test with the mock model passed: 583 rulings imported, UI 200, all endpoints respond.
