"""Command line entry point.  Run from the src/ directory:  python -m suva <command>

  scrape   --days 92           fetch bger.ch publications into the database (no LLM)
  triage   [--all]             score judgements not yet assessed (and summarise relevant ones)
  run      --days 92           scrape + triage + summarise in one go
  add      8C_145/2025         fetch, assess and summarise one judgement
  demo                         load the 54 Suva example summaries as demo cards (no bger.ch needed)
  eval                         recall/precision of the ranking against the Suva Excel list
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


def main():
    p = argparse.ArgumentParser(prog="suva", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("scrape", "run"):
        s = sub.add_parser(name)
        s.add_argument("--days", type=int, default=92)
        s.add_argument("--divisions", default="", help="only fetch full text for these, e.g. 8C,9C,4A")
    t = sub.add_parser("triage")
    t.add_argument("--all", action="store_true")
    a = sub.add_parser("add")
    a.add_argument("docket")
    sub.add_parser("demo")
    sub.add_parser("eval")
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    args = p.parse_args()

    if config.USE_MOCK_LLM and args.cmd in ("run", "triage", "add", "demo"):
        print("! LLM_BASE_URL not set: using the MOCK model (output is labelled 'mock').", file=sys.stderr)
    if args.cmd == "scrape":
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
    elif args.cmd == "serve":
        import uvicorn
        uvicorn.run("suva.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
