# Lex Aperta — Architecture

> Placeholder. Fill this in as the design settles. The judge-facing write-up lives in
> `technical_report.md` §2.

## Intended pipeline

1. **Ingest**: fetch bger.ch publications (last 3 months) and the provided `judgements/` exports.
2. **Triage**: Apertus v1.5 gives each judgement a relevance score plus a written explanation.
3. **Summarise**: Apertus v1.5 writes DE and FR summaries in Suva's style.
4. **Store**: a searchable knowledge base of judgements, scores and summaries.
5. **UI**: a web app for Suva's legal experts.

## Runtime constraints

- LLM access only through `LLM_NAME` / `LLM_BASE_URL` / `LLM_API_KEY` (an OpenAI-compatible endpoint).
- No other external services at runtime, so it can run air-gapped or on-prem.
