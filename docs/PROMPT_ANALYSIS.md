# Summary prompt: what Suva's summaries actually look like (Fri 27 Nov, ~17:00)

Measured on Suva's 54 expert summaries (`data/examples.json`) and on 38 of the same rulings summarised blind
by our pipeline (`data/examples_compare.json`, page `/lex/examples`). Our 38 were generated with the prompt
**before** PR #16 (Paul's "shorter Suva-style summaries"). The last column checks PR #16 against Suva's data.

| Feature (DE unless noted) | Suva (median / share) | Ours (old prompt) | PR #16 prompt says | Verdict on PR #16 |
|---|---|---|---|---|
| Length DE | **180 words** (IQR 109–242) | 212 | 100–170 | too short, aim ~120–240 |
| Length FR | **227 words** (IQR 131–287) | 263 | 100–180 | too short; FR is ~25 % longer than DE at Suva |
| Sentences | 9, long (17 words/sentence) | 18, short (11 words) | – | ours too choppy, ask for fewer, longer sentences |
| Opening | **principle first: 76 % DE, 89 % FR** | facts first: 63 % DE, 82 % FR | "In diesem Urteil prüfte das Bundesgericht …" preferred | the example opener is rare at Suva (3 %); prefer the rule itself |
| Tense | **present tense in 38 of 54** (rule statements: "ist legitimiert", "muss er …") | mixed | "always past tense, never present" | **wrong**: Suva states the rule in present tense |
| Names the Federal Court | median **0** times | 2–3 times | – | impersonal: state the rule, not "das Bundesgericht erwog" |
| Consideration refs "(E. x)" | median **0** (a third of summaries cite) | 4 | 1–2 | OK; keep 1–2 for navigation |
| Dates in text | median 0 | 2 | "no dates" | OK |
| Outcome sentence | DE 32 %, FR 53 % | DE 55 %, FR 95 % | always at the end | optional; Suva often ends on the principle |
| Content-word overlap with Suva | – | DE 19 %, FR 23 % | – | baseline to beat |

Typical Suva openings: "Erwartet der Versicherer von einer arbeitsunfähigen versicherten Person … einen
Berufswechsel, muss er …", "Die Reinigung von Wohnungen und Büros fällt unter Art. 73 …", "Die Sozialhilfebehörde,
die eine versicherte Person regelmässig unterstützt, ist legitimiert, … anzufechten."

## Proposed prompt changes (on top of PR #16)

1. **Open with the rule (Leitsatz)**, in the present tense, impersonal: what applies from now on, as one sentence a
   lawyer can quote. Only then 1–2 sentences of facts (generic: "Ein Versicherter, Maurer, …"; no dates, places,
   amounts unless decisive), then the reasoning.
2. **Tense:** rule statements in the present tense; what happened in the case may be in the past tense.
3. **Length:** DE 120–240 words, FR 150–290 words (Suva's interquartile range); FR may be longer than DE.
4. **Fewer, longer sentences** (8–10); no "Das Bundesgericht erwog …" in every sentence. Name the court at most once.
5. **Outcome:** one short sentence only when it matters for practice; never contradict the Dispositiv (our check stays).
6. **Citations:** 1–2 "(E. x)" on the key rule (kept for jump links). Suva cites in a third of cases; navigation helps the jury.

## How to test (before rolling out)

Run old (PR #16) vs proposed prompt on the same ~10 example rulings, blind, and compare on `/lex/examples`:
principle-first share, present-tense share, words, sentence length, overlap with Suva. Then read 3–4 pairs.
Suva's quality score uses its **top-5 summaries for June 2026**, so style match matters as much as content.
