# Lex Aperta — status (Fri 27 Nov 2026, afternoon)

For Paul (and Paul's AI): where Miguel's side stands, what we found, what we propose.
The API/data contract is in [`docs/API.md`](API.md).

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

## Asks for Paul

1. Static mode in `app.js` (one URL switch, read-only, see API.md) and a `pages.yml` workflow; enable Pages in repo settings.
2. "Summarise another ruling" on Pages: issue template + Action (can wait until the export works).
3. OK on the additive card fields in API.md (`areas`, `procedural`, `dataset`, `expert_summaries`)?

## Small findings from reviewing PR #1 (merged)

- Server needs Python ≥ 3.10 (`str | None` in `server.py` fails on the Mac's 3.9). Document it or add `from __future__ import annotations`.
- Cards imported from the crawl have an empty `subject`. The subject line ("Gegenstand/Objet") can be taken from the ruling text (`prefilter.SUBJECT`).
- Smoke test with the mock model passed: 583 rulings imported, UI 200, all endpoints respond.
