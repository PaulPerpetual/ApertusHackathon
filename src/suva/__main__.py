"""Command line entry point.  Run from the src/ directory:  python -m suva <command>

  import   ../data/period/<from>_<to>   triage + summarise a crawl made with src/crawl_period.py
  scrape   --days 92           fallback: fetch directly from bger.ch (often blocked) into the database
  triage   [--all]             score judgements not yet assessed (and summarise relevant ones)
  run      --days 92           scrape + triage + summarise in one go
  add      8C_145/2025         fetch, assess and summarise one judgement
  demo                         load the 54 Suva example summaries as demo cards (no bger.ch needed)
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
    n = 0
    for j in scraper.load_crawled(args.folder, divisions):
        pipeline.process(j, exs)
        n += 1
    print(f"{n} judgements processed into {config.DB_PATH}")


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
    i.add_argument("folder")
    i.add_argument("--divisions", default="", help="e.g. 8C,9C,4A")
    t = sub.add_parser("triage")
    t.add_argument("--all", action="store_true")
    a = sub.add_parser("add")
    a.add_argument("docket")
    sub.add_parser("demo")
    sub.add_parser("eval")
    e = sub.add_parser("export")
    e.add_argument("folder", nargs="?", default=str(config.ROOT / "site"))
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    args = p.parse_args()

    if config.USE_MOCK_LLM and args.cmd in ("run", "import", "triage", "add", "demo"):
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
    elif args.cmd == "eval":
        cmd_eval(args)
    elif args.cmd == "export":
        cmd_export(args)
    elif args.cmd == "serve":
        import uvicorn
        uvicorn.run("suva.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
