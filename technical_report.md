# Technical report — Lex Aperta, `team name`

A deeper write-up than the README: what we built, how it works, and what the numbers say.

- **Challenge partner:** Suva
- **Challenge:** Identification of relevant Federal Court judgements and preparation of a legal summary
- **Event:** On-site Zurich
- **Team:** `team name` — Paul, Miguel
- **Demo:** `link to video`
- **Live prototype:** <https://api.robotross.art/lex/> (read-only showcase: <https://paulperpetual.github.io/ApertusHackathon/>)

## 1. Summary

Each quarter, Suva's lawyers go through every new ruling of the Federal Supreme Court. They pick the ones that matter
for accident insurance and write a short German and French summary of each. **Lex Aperta** does the first pass
with **Apertus v1.5 70B** and nothing else:

1. Crawl all rulings of the period.
2. Prefilter by subject area.
3. Run four Apertus passes that sort each ruling into *relevant*, *borderline (Grenzfall)* or *not relevant*, each
   with a reason.
4. Rank the list.
5. Write DE and FR summaries in Suva's style, with clickable references to the considerations (E. x).

Lawyers work in a web app modelled on a mail client. They see a ranked list with score, reason and tags. The detail
panel shows the original ruling and both summaries. Buttons let them confirm, reject or edit a ruling, and
"Urteil zusammenfassen" adds any further ruling on demand.

**Headline results:**
- On Suva's 82 example rulings, the relevance pipeline finds **98 %** of the rulings Suva summarised (recall).
- On the labelled window Oct 2025 – Mar 2026, **53 %** of our top 5 are on Suva's list (34 % before ranking work).
- Summaries cover **92 %** of the legal points in Suva's own summaries on the development half, and
  **94.7 %** on the hold-out half (prompt S2.2).

## 2. Architecture

```
entscheidsuche.ch ─ crawl_period.py ─▶ SQLite ─ prefilter (division + subject) ─▶ Apertus passes 1–4 (relevance, tier, reason, tags)
                                                                               └▶ Apertus pass 5 + learned weights (ranking)
                                                                               └▶ Apertus extract → write DE / write FR (summaries)
                                                                               └▶ postcheck (rule-based checks, one guarded retry)
FastAPI (server.py) ◀── plain HTML/JS UI (no build step): list · Trefferliste · detail panel · edit history
```

The components are listed below.

| Component | Files | Role |
| --- | --- | --- |
| Crawl | `src/crawl_period.py`, `src/suva/scraper.py` | Rulings of a period via entscheidsuche.ch (bger.ch blocks scripts); single rulings on demand |
| Prefilter | `src/prefilter.py`, `src/suva/triage.py` | Divisions 8C/9C/4A plus subject-area keywords; no LLM |
| Relevance | `triage.py`, `iv_pass.py`, `rescue_pass.py`, `adjudicate.py` | Pass 1 scores the ruling. Pass 2 re-checks IV rulings that set a transferable rule. Pass 3 rescues ATSG procedure rulings. Pass 4 is a critical review that sorts into Tier 1 / Grenzfall / not relevant, with a reason. |
| Ranking | `rank_pass.py`, `src/tiebreak_top.py`, `src/learn_ranking.py` | Apertus rates importance 0–100 and orders the tied top directly. A logistic model trained on Suva's labelled list weights Apertus' own sub-judgements. |
| Summaries | `summarize_v2.py`, `explain.py`, `tags.py` | Apertus first extracts the key considerations with their E. numbers. It then writes DE and FR separately, few-shot with the most similar Suva examples and a DE↔FR glossary. |
| Quality checks | `postcheck.py` | Rule-based checks of every summary, then one guarded retry and mechanical clean-up (see below) |
| App | `server.py`, `static/` | FastAPI + SQLite. Human decisions, score overrides and edited texts are stored next to the AI output, with a full edit history. |

**Quality checks (postcheck).** Every generated summary and reason is checked by rules before it is stored:

- Outcome against the operative part (Dispositiv): "appeal rejected" must not read "admitted" or "remanded".
- Wrong language, or citations in the wrong language (BGE/E. in DE, ATF/consid. in FR).
- Costs, dates and birth years.
- Leaked table cells.
- The accident insurer named in pure invalidity-insurance rulings.
- Known mistranslations, such as OPGA in German text.
- Length.

A failed check triggers one retry with the specific problem named. The retry is accepted only if it has fewer problems
and is not a meta answer. Cut-off sentences, table remnants and cost sentences are also cleaned at display time.

### Target architecture (mandatory)

Lex Aperta is deployable as **a) on-premise**, **b) air-gapped** and **c) sovereign Swiss cloud**.

- One Docker image (`Dockerfile`) holds UI, API and pipeline. State is a single SQLite file on a mounted volume.
- The only runtime dependency is an OpenAI-compatible LLM endpoint, set by `LLM_NAME`, `LLM_BASE_URL` and
  `LLM_API_KEY`. With Apertus served locally (e.g. vLLM on a GPU server), no external connection is needed at runtime.
  New rulings are then imported as files (`python -m suva import <folder>`) instead of being crawled.
- The UI loads no external scripts, fonts or CDNs.
- **Build time:** pip packages (`requirements.txt`: fastapi, uvicorn, httpx, beautifulsoup4, openpyxl, python-dotenv).
- **Runtime:** LLM endpoint. Optionally entscheidsuche.ch for crawling and adding single rulings.
- **Azure (bonus):** the same image runs on Azure Container Apps or App Service in region Switzerland North, with an
  Azure Files share at `/app/data`. Apertus runs on an Azure GPU VM/AKS with vLLM, or on any Swiss-hosted endpoint.

## 3. Use of Apertus

- **Model:** `swiss-ai/Apertus-v1.5-70B` (`apertus-v1-5-70b`)
- **How it is used:** inference only. There is no fine-tuning. Few-shot prompting with Suva's example summaries
  plus multi-pass prompting.
- **Where it runs:** hosted endpoint, the CSCS / Keera gateway (`https://gateway.keera.ch/api/v1`, OpenAI-compatible).
  Any other OpenAI-compatible Apertus endpoint works unchanged.

**Every decision on the submitted list and every text comes from Apertus.** Other models (GPT, Gemini, Claude) were
used only during development, as blind benchmark rankings on `/compare`. They never enter the list or its order.
Prompts are in the files listed in §2. Settings:
- temperature 0 for scoring, 0.7 with 3 samples in the recall pass;
- input truncated to `LLM_MAX_INPUT_CHARS` (default 24 000 characters);
- JSON output parsed with a fallback.

Without `LLM_BASE_URL` the app runs against a labelled mock model, so the UI can be developed offline.

## 4. Data

- **Rulings:** Federal Supreme Court rulings, retrieved via entscheidsuche.ch. These are public court decisions,
  already anonymised by the court. Period processed: April – June 2026.
- **Suva material** (from the challenge repo):
  - 54 example summaries (`judgements/*.html`), used as few-shot examples and for evaluation.
  - The Q4 2025 / Q1 2026 list (`judgements/BG_Urteile_2025_Q4_2026_Q1.xlsx`), used as relevance labels.
  - The examples are split into dev and hold-out halves (`data/examples_split.json`). The model never sees Suva's
    summary of the ruling it is writing.
- **No personal data** beyond what the court publishes. Editors in the app are identified only by a typed name.

## 5. Evaluation

**Relevance** (labelled window Oct 2025 – Mar 2026, Suva's yes/no list; Suva scores recall and F2):

| Version | Recall | Note |
| --- | --- | --- |
| Pass 1 only | 77 % on Suva's example rulings | |
| Passes 1–4 (Tier 1 + Grenzfall) | **98 %** on Suva's example rulings, 98 % on the labelled window | Grenzfälle always rank below Tier 1 |
| Ranking: share of our top 5 on Suva's list | 34 % → **53 %** | after the ranking pass and tie-break |

Submitted Q2 2026 list: **163 rulings = 77 relevant + 86 Grenzfälle** (`data/submission/`).

**Summaries.** Each Suva example is broken into legal points (`data/eval_gold_points.json`). We then measure how many
of them our summary covers, and count error types (`src/eval_summaries.py`):
- Development half: 92 % of Suva's points covered, no error types.
- Hold-out half: 94.7 %.

**Expert review.** We also reviewed the top 10 by hand against the original rulings, as a lawyer would. We used it
only as an error analysis and did not correct the submitted texts by hand. Error types we found and how they are
handled:
- Reversed or invented outcomes: Dispositiv check.
- Dates and costs in the text: postcheck.
- Wrong-language legal abbreviations: postcheck.
- IV rulings framed as accident insurance: postcheck.
- Formulaic openings: prompt.
- Reasons cut off mid-sentence: display-time clean-up.

## 6. Limitations

- **Apertus output varies strongly between runs.** A prompt change has to be judged on the dev set, not on single
  samples.
- **Fabricated or wrong details still occur.** Roughly 1 in 4 German summaries of the examples had a wrong detail,
  such as an invented last sentence or a muddled legal concept. French is clearly better. The checks catch formal
  errors, not every factual one.
- **Ranking at the very top is the weakest part.** Benchmark models rank Suva's picks better (AUC 0.90–0.94 vs 0.75)
  and agree with Apertus on only 3 of the top 10.
- **Some procedural IV/ATSG rulings are still missed.** Five rulings flagged by a benchmark model are not on our
  list, because only Apertus decides.
- **Not tested:** throughput for a full year, multiple concurrent editors, and accessibility.

## 7. Reproducibility

```bash
git clone https://github.com/PaulPerpetual/ApertusHackathon.git && cd ApertusHackathon
pip install -r requirements.txt                       # Python 3.9+
cp .env.example .env                                  # set LLM_NAME, LLM_BASE_URL, LLM_API_KEY
cd src
python crawl_period.py --from 2026-04-01 --to 2026-06-30
python -m suva import ../data/period/2026-04-01_2026-06-30 --divisions 8C,9C,4A   # triage + summaries
python -m suva serve                                  # http://127.0.0.1:8000
# or: docker build -t lex . && docker run -p 8000:8000 --env-file .env lex
```

Evaluation:

```bash
python -m suva eval                                   # recall against Suva's Excel list
python src/build_eval_db.py data/eval_window.sqlite   # rebuild the labelled window DB
python src/eval_f2.py data/eval_window.sqlite --variants
python src/eval_summaries.py                          # summary coverage on dev / hold-out
```

- **Hardware:** any laptop or server; the model runs behind the endpoint.
- **Runtime:** about 1–2 h of LLM calls for one quarter (~2,000 rulings, ~180 after prefilter).
- **Exact commit:** `<commit hash at submission>`.
- **Runs:** all model outputs used for the numbers above are in `data/runs/`.

## License

Creative Commons Attribution 4.0 (CC-BY-4.0). All HackApertus projects are open-sourced.
