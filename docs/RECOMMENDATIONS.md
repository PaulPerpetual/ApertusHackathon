# Prompt & pipeline recommendations: Claude, Codi (Codex), Gem (Gemini), Fri 27 Nov ~17:30

Three independent reviews of our output against Suva's expert summaries (`/lex/examples`, 38 rulings processed blind).
This merges them, says what we adopt and why, and what's already implemented. Details:
[`PROMPT_ANALYSIS.md`](PROMPT_ANALYSIS.md) (Claude's measurements).

## 1. Where the reviews agree (adopt)

| # | Finding | Who | Evidence | Status |
|---|---|---|---|---|
| A | **Lead with the legal rule, not a case report.** Suva opens with the rule (76 % DE, 89 % FR); we open with facts (63 % / 82 %) in a fixed template (birth/job, accident date, lower court, "Streitig war…", "Das Bundesgericht erwog…", costs). | all three | 8C_44/2025: Suva = 1 sentence (standing of social-assistance authority); ours = medical evidence | v2 prompt |
| B | **Wrong outcome is fatal.** Remand ≠ final rejection or award. | all three | 8C_517/2024 (remand stated as rejection), 8C_334/2025 title vs summary, 8C_484/2025 | Dispositiv check live; v2 also distinguishes remands |
| C | **Fewer citations, never boilerplate.** Suva: median 0, a third cite 1–3. Ours: median 4, incl. E. 1 and costs. | all three | | v2: 1–2 on the key rule, never E. 1/costs |
| D | **No dates, birth years, court costs, lower-court file numbers.** | all three | | v2 |
| E | **Length follows substance.** Suva 8–673 words (median DE 180, FR 227; FR ~25 % longer). | Claude, Gem | 8C_455/2025: Suva 31 words, ours 129 | v2: 30–100 words for one procedural point, 120–240 / 150–290 for complex cases |
| F | **French is its own text** with ATF terminology. | Gem (slide 4), Claude | | already separate; v2 reinforces |

## 2. New error types (adopt as automatic checks, not just prompt text)

| # | Error | Who | Example | Fix (v2) |
|---|---|---|---|---|
| G | **Wrong insurer named "Suva"** | Gem | 8C_366/2024 (AXA → "Suva-Ärzte"), 8C_318/2025 (Generali → Suva); **also in relabel output now**: 8C_395/2025 (IV case, Begründung says "die Suva muss …") | check: "Suva" in text but not in the ruling → forced correction; `SUVA_ALIAS` only applied when Suva is a party |
| H | **French abbreviations in German** (LAA, LPGA, OLAA, CNA …) and vice versa | Gem | | deterministic replacement LAA→UVG, LPGA→ATSG, OLAA→UVV, LAI→IVG, RAI→IVV, ESS→LSE (and reverse for FR) |
| I | **Mistranslated legal terms** | Gem, Codi | "Gefahrengemeinschaft" for *relatives Wagnis* (8C_176/2025), "Bandagenverletzung" (sagittal band), "Genugtung" | glossary extended (Wagnis, Listenverletzung, Distorsion/Kontusion, Untersuchungshaft …) |
| J | **Anonymisation gaps** ("in ansässige Gesellschaft", "Bericht des Dr. vom") | Gem | 8C_129/2025 | check + neutral wording |
| K | **Generalising medical findings into rules** | Codi | 8C_275/2025: individual healing time became a "six-week rule" | v2: separate party claims / medical assessment / lower court / Federal Court; only the Court's assessment is a rule |
| L | **Flattening conditional findings** | Codi | 8C_348/2025: adequacy criteria "left open" reported as "not met" | v2 extraction records status: affirmed / denied / left open / assumed |
| M | **Mixing legal concepts** | Codi | 8C_178/2025: insured earnings vs hypothetical valid income | v2 extraction: precise question + concept first |

## 3. Workflow changes (adopt)

| # | Change | Who | Status |
|---|---|---|---|
| N | **Extract propositions before writing prose:** question, answer, conditions/exceptions, status, consideration, transfers to UVG?, then pick the focus. | Codi | v2 step 1 |
| O | **Full input:** the old excerpt (24k chars) could cut the end of the reasoning. Always pass all considerations + Dispositiv; shorten only the middle, and tell the model. | Codi | v2 (`full_input`) |
| P | **One assessment for title, score, Begründung, summary.** Today they come from separate steps (triage, explain, relabel, summarize), so they can contradict each other (8C_334/2025, 8C_241/2025). | Codi | **open**: proposal below |
| Q | **Evaluate on held-out data** with meaningful measures: recovery of Suva's propositions, wrong outcomes, unsupported generalisations, citation correctness, not word overlap. | Codi | 38 examples split 19 dev / 19 hold-out (`data/examples_split.json`); A/B on dev running |

## 4. Where we disagree (with data)

**Triage: "rate every IV/ATSG ruling ≥ 60, lower the threshold to 50" (Gem), "judge by transferable rule, not branch" (Codi).**
Right in principle, and it explains 7 of 10 misses on the examples. But the examples contain only Suva's positives, so they
can't show the cost. On the realistic labelled window (733 rulings, 58 Suva picks) we tested exactly this twice:

| Selection | Listed | Recall | Precision | F2 |
|---|---|---|---|---|
| **v1 (production)** | 101 | 84 % | 49 % | **0.736** |
| v2 "general rule vs individual case" | 259 | 98 % | 22 % | 0.580 |
| v3 "ATSG rescue" with mandatory quote | 211 | 91 % | 25 % | 0.598 |

Apertus can't reliably tell "clarifies an ATSG rule" from "applies one", so it flags almost everything. A threshold of 50
changes nothing (scores are bimodal: 0–15 or 60+). **Keep v1 for selection**; use Codi's transferability test in the
*texts* (Begründung/summary), where it improves accuracy without changing the hit list. See `/lex/compare`.

**Outcome sentence:** Gem says always end with the outcome; Suva does so in 32 % (DE) / 53 % (FR). v2: one short outcome
sentence when it matters for practice (always for remands), never contradicting the Dispositiv.

**Tense:** PR #16 prescribes past tense only. Suva writes rule statements in the **present** (38 of 54). v2: rule in
present tense, case facts may be past.

## 5. Decisions for Paul

1. **Summary prompt:** adopt v2 (`src/suva/summarize_v2.py`) if it wins the A/B on the dev half (running now: PR #16
   prompt vs v2, 19 rulings each). Then confirm on the 19 hold-out rulings, then regenerate the 77 hit-list summaries.
2. **Consistency (P):** derive title + Begründung from the same proposition extraction as the summary (v2 step 1),
   instead of separate triage/explain/relabel calls. Proposal: `relabel` reads `summaries.notes` (FOKUS + ERGEBNIS)
   when present. Paul owns `relabel`, OK?
3. **"Suva" check for relabel:** the same check as G (8C_395/2025 shows the problem in the current Begründung).

## 6. Status right now (live on https://api.robotross.art/lex/)

- Hit list unchanged: 77 rulings, F2 0.736 on the labelled window.
- `relabel` (Paul's new short Begründung, ≤ 40 words) ran on all 77 and is deployed (33/33 smoke test).
- Summaries in production are still from the pre-#16 prompt; they get regenerated once the A/B has a winner.
