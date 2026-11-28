"""Glue: judgement -> prefilter -> LLM triage -> (if relevant) DE/FR summaries -> database."""
from . import config, db, examples as ex_mod, llm, summarize, summarize_v2, triage

PREFILTER_MIN = 20  # below this, store a rule-based "not relevant" assessment without calling the LLM


def process(j, examples=None, force_summary=False, log=print):
    examples = examples if examples is not None else ex_mod.load_examples()
    # never show the model Suva's own summary of the same judgement (would leak the answer)
    shots = [e for e in examples if e["docket"] != j["docket"]]
    pre, hits = triage.prefilter(j)
    with db.connect() as con:
        slug = db.upsert_judgement(con, j)
    if pre < PREFILTER_MIN and not force_summary:
        a = {"score": pre, "suva_party": False, "tags": [],
             "title_de": j.get("subject") or j["docket"], "title_fr": j.get("subject") or j["docket"],
             "explanation_de": "Vorfilter: keine Bezüge zur Unfallversicherung gefunden.",
             "explanation_fr": "Préfiltre: aucun lien avec l'assurance-accidents trouvé."}
        model = "prefilter"
    else:
        a = triage.assess(j, triage.topic_hint(shots))
        model = llm.model_name()
    if model != "prefilter" and j.get("text"):
        try:  # specific Begründung (legal question first, deciding consideration), same as the list (src/run_explanations.py)
            from . import explain
            x = explain.explain(j, a.get("score"))
            if x.get("de"):
                a["explanation_de"], a["explanation_fr"] = x["de"], x.get("fr") or a.get("explanation_fr")
        except Exception as e:  # keep the triage text rather than failing the whole job
            log(f"  explain failed for {j['docket']}: {e}")
    with db.connect() as con:
        db.save_assessment(con, slug, a, model, pre)
    log(f"{j['docket']}: prefilter={pre} score={a['score']} ({model})")
    if (a["score"] >= config.RELEVANCE_SUMMARY_THRESHOLD or force_summary) and j.get("text"):
        s = summarize_v2.summarize(j, shots)  # S2.2, the prompt confirmed on the hold-out (same as the list)
        with db.connect() as con:
            for lang in ("de", "fr"):
                db.save_summary(con, slug, lang, s[lang], llm.model_name())
        log(f"  summarised {j['docket']}")
    return slug
