"""Command line entry point.  Run from the src/ directory:  python -m suva <command>

  import   ../data/period/<from>_<to>   triage + summarise a crawl made with src/crawl_period.py
  scrape   --days 92           fallback: fetch directly from bger.ch (often blocked) into the database
  triage   [--all]             score judgements not yet assessed (and summarise relevant ones)
  run      --days 92           scrape + triage + summarise in one go
  add      8C_145/2025         fetch, assess and summarise one judgement
  demo                         load the 54 Suva example summaries as demo cards (no bger.ch needed)
  relabel  [--min 20]          rewrite titles short and in the right language + French tags, from the existing assessment
  tags-fr                      add French tags to rulings triaged before tags_fr existed (one short LLM call each)
  eval                         recall/precision of the ranking against the Suva Excel list
  export   ../site             write static JSON mirroring the API (GitHub Pages / intranet web server)
  serve    --port 8000         start the web UI
"""
import argparse
import sys

from . import config, db, examples, pipeline, scraper


def cmd_scrape(args, process=False):
    exs = examples.load_examples()
    divisions = set(args.divisions.split(",")) if args.divisions else None
    n = 0
    for j in scraper.scrape(days=args.days, divisions=divisions):
        if process:
            pipeline.process(j, exs)
        else:
            with db.connect() as con:
                db.upsert_judgement(con, j)
        n += 1
    print(f"{n} judgements stored in {config.DB_PATH}")


def cmd_import(args):
    exs = examples.load_examples()
    divisions = set(args.divisions.split(",")) if args.divisions else None
    jobs = list(scraper.load_crawled(args.folder, divisions))
    workers = max(1, getattr(args, "workers", 1) or 1)
    if workers == 1:
        for j in jobs:
            pipeline.process(j, exs)
    else:  # Apertus calls dominate; run several in parallel (SQLite writes are short, db.connect waits)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(workers) as pool:
            futs = {pool.submit(pipeline.process, j, exs): j["docket"] for j in jobs}
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:  # keep going; report at the end
                    print(f"! {futs[f]}: {e}", file=sys.stderr)
    print(f"{len(jobs)} judgements processed into {config.DB_PATH}")


def cmd_triage(args):
    exs = examples.load_examples()
    with db.connect() as con:
        q = "SELECT * FROM judgements" if args.all else \
            "SELECT j.* FROM judgements j LEFT JOIN assessments a ON a.slug=j.slug WHERE a.slug IS NULL"
        rows = [dict(r) for r in con.execute(q)]
    for j in rows:
        pipeline.process(j, exs)


def cmd_add(args):
    j = scraper.fetch_single(args.docket)
    pipeline.process(j, force_summary=True)


def cmd_demo(args):
    """Demo data: the Suva example summaries become cards; triage runs on the summary text.
    Clearly marked as source='demo' in the UI."""
    from . import llm, triage
    exs = examples.load_examples(refresh=True)
    gt = examples.load_ground_truth()
    for ex in exs:
        j = {"docket": ex["docket"], "division": ex["docket"].split("_")[0], "url": ex["url"],
             "subject": ex["title"], "text": ex["de"] + "\n\n" + ex["fr"], "source": "demo",
             "decision_date": None, "publication_date": gt.get(ex["docket"])}
        with db.connect() as con:
            slug = db.upsert_judgement(con, j)
        a = triage.assess(j)
        with db.connect() as con:
            db.save_assessment(con, slug, a, llm.model_name(), triage.prefilter(j)[0])
            for lang in ("de", "fr"):
                db.save_summary(con, slug, lang, ex[lang], "suva-human-example")
        print(f"{ex['docket']}: {a['score']}")


def cmd_tags_fr(args):
    """Backfill assessments.tags_fr for rows that only have German tags. Keeps the order 1:1."""
    import json
    from . import llm
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(
            "SELECT slug, tags FROM assessments WHERE tags IS NOT NULL AND tags != '[]' AND (tags_fr IS NULL OR tags_fr = '[]')")]
    for r in rows:
        de = json.loads(r["tags"])
        out = llm.chat([{"role": "system", "content": "Übersetze juristische Schlagworte des Schweizer Sozialversicherungsrechts "
                         "ins Französische (Fachbegriffe wie in BGE/ATF, z.B. Unfallversicherung = assurance-accidents). "
                         'Antworte nur mit JSON: {"tags_fr": [...]} in derselben Reihenfolge.'},
                        {"role": "user", "content": json.dumps({"tags": de}, ensure_ascii=False)}],
                       temperature=0.0, max_tokens=200, json_mode=True)
        try:
            fr = [str(t)[:40] for t in llm.parse_json(out).get("tags_fr") or []]
        except ValueError:
            fr = []
        if len(fr) != len(de):
            print(f"! {r['slug']}: skipped (got {len(fr)} of {len(de)} tags)", file=sys.stderr)
            continue
        with db.connect() as con:
            con.execute("UPDATE assessments SET tags_fr=? WHERE slug=?", (json.dumps(fr, ensure_ascii=False), r["slug"]))
        print(f"{r['slug']}: {', '.join(fr)}")


RELABEL_SYSTEM = """Du erhältst die Bewertung eines Bundesgerichtsurteils (Titel, Begründung, deutsche Schlagworte).
Schreibe kurze, einheitliche Listentitel und übersetze die Schlagworte.
- title_de: DEUTSCH, 4-8 Wörter, Kernfrage + Ergebnis, ohne Aktenzeichen (z.B. "Komplementärrente: IV-Rente nur anteilig anrechnen").
- title_fr: FRANÇAIS, 4-8 mots, même contenu (z.B. "Rente complémentaire: rente AI prise en compte au prorata").
- tags_fr: dieselben Schlagworte auf Französisch, gleiche Reihenfolge, Fachbegriffe wie in den ATF.
Antworte nur mit JSON: {"title_de": "...", "title_fr": "...", "tags_fr": [...]}"""


def cmd_relabel(args):
    """Short, language-correct titles and French tags for rulings already triaged (one short LLM call each)."""
    import json
    from . import llm
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(
            "SELECT slug, title_de, title_fr, explanation_de, tags FROM assessments "
            "WHERE model != 'prefilter' AND COALESCE(score_override, ai_score) >= ?", (args.min,))]
    for r in rows:
        de = json.loads(r["tags"] or "[]")
        user = json.dumps({"title_de": r["title_de"], "title_fr": r["title_fr"], "explanation_de": r["explanation_de"],
                           "tags": de}, ensure_ascii=False)
        try:
            a = llm.parse_json(llm.chat([{"role": "system", "content": RELABEL_SYSTEM}, {"role": "user", "content": user}],
                                        temperature=0.0, max_tokens=300, json_mode=True))
        except (ValueError, llm.LLMError) as e:
            print(f"! {r['slug']}: {e}", file=sys.stderr)
            continue
        fr = [str(t)[:40] for t in a.get("tags_fr") or []]
        sets = {"title_de": str(a.get("title_de") or "").strip()[:120], "title_fr": str(a.get("title_fr") or "").strip()[:120]}
        sets = {k: v for k, v in sets.items() if v}
        if len(fr) == len(de):
            sets["tags_fr"] = json.dumps(fr, ensure_ascii=False)
        if sets:
            with db.connect() as con:
                con.execute(f"UPDATE assessments SET {', '.join(k + '=?' for k in sets)} WHERE slug=?", (*sets.values(), r["slug"]))
        print(f"{r['slug']}: {sets.get('title_de', '-')}")


def cmd_eval(args):
    gt = examples.load_ground_truth()
    with db.connect() as con:
        cards = [c for c in db.list_cards(con) if c["source"] != "demo"]
    if not cards:
        sys.exit("No scraped judgements in the database. Run `python -m suva run` first.")
    ranked = [c["docket"] for c in cards]
    in_db = [d for d in gt if d in set(ranked)]
    print(f"Ground truth dockets: {len(gt)}; present in scraped window: {len(in_db)}")
    for k in (10, 30, 60, 100):
        top = set(ranked[:k])
        hits = len(top & set(gt))
        print(f"  top-{k:<3}  hits={hits:<3} precision={hits / k:.2f}  recall={hits / max(1, len(in_db)):.2f}")
    missed = [d for d in in_db if d not in set(ranked[:30])]
    print("Missed in top-30:", ", ".join(missed) or "none")


def cmd_export(args):
    """Static mirror of the read API (docs/API.md): api/<path>.json for every GET the UI makes."""
    import json
    from datetime import datetime, timezone
    from pathlib import Path
    from . import llm, server
    out = Path(args.folder) / "api"
    (out / "judgements").mkdir(parents=True, exist_ok=True)
    (out / "kb" / "example").mkdir(parents=True, exist_ok=True)

    def dump(rel, obj):
        (out / rel).write_text(json.dumps(obj, ensure_ascii=False, default=str), encoding="utf-8")

    with db.connect() as con:
        cards = db.list_cards(con)
        dump("judgements.json", cards)
        for c in cards:
            dump(f"judgements/{c['slug']}.json", db.get_detail(con, c["slug"]))
    dump("status.json", {"model": llm.model_name(), "mock": config.USE_MOCK_LLM, "threshold": config.RELEVANCE_SUMMARY_THRESHOLD,
                         "read_only": True, "static": True, "jobs": {},
                         "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    dump("kb.json", server.kb_entries())
    for ex in examples.load_examples():
        dump(f"kb/example/{db.slugify(ex['docket'])}.json", ex)
    print(f"exported {len(cards)} judgements to {out}")


def main():
    p = argparse.ArgumentParser(prog="suva", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("scrape", "run"):
        s = sub.add_parser(name)
        s.add_argument("--days", type=int, default=92)
        s.add_argument("--divisions", default="", help="only fetch full text for these, e.g. 8C,9C,4A")
    i = sub.add_parser("import")
    i.add_argument("--workers", type=int, default=1, help="parallel LLM workers")
    i.add_argument("folder")
    i.add_argument("--divisions", default="", help="e.g. 8C,9C,4A")
    t = sub.add_parser("triage")
    t.add_argument("--all", action="store_true")
    a = sub.add_parser("add")
    a.add_argument("docket")
    sub.add_parser("demo")
    sub.add_parser("eval")
    sub.add_parser("tags-fr")
    rl = sub.add_parser("relabel")
    rl.add_argument("--min", type=int, default=20, help="only rulings with at least this relevance score")
    e = sub.add_parser("export")
    e.add_argument("folder", nargs="?", default=str(config.ROOT / "site"))
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    args = p.parse_args()

    if config.USE_MOCK_LLM and args.cmd in ("run", "import", "triage", "add", "demo", "tags-fr", "relabel"):
        print("! LLM_BASE_URL not set: using the MOCK model (output is labelled 'mock').", file=sys.stderr)
    if args.cmd == "import":
        cmd_import(args)
    elif args.cmd == "scrape":
        cmd_scrape(args)
    elif args.cmd == "run":
        cmd_scrape(args, process=True)
    elif args.cmd == "triage":
        cmd_triage(args)
    elif args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "demo":
        cmd_demo(args)
    elif args.cmd == "relabel":
        cmd_relabel(args)
    elif args.cmd == "tags-fr":
        cmd_tags_fr(args)
    elif args.cmd == "eval":
        cmd_eval(args)
    elif args.cmd == "export":
        cmd_export(args)
    elif args.cmd == "serve":
        import uvicorn
        uvicorn.run("suva.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
