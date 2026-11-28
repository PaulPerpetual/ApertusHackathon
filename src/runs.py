"""Runs: comparable outputs of models / agents / versions, for the Compare tab (/compare).

A run = one model's yes/no + score + reason per ruling on one dataset. Stored as
  data/runs/<dataset>/<run_id>.jsonl   first line {"run", "model", "dataset", "created_at", "notes"},
                                       then one {"docket", "score", "relevant", "reason"} per ruling
  data/runs/<dataset>/_dockets.json    subject, date, title, url, Suva label (if known) per docket
  data/runs/index.json                 datasets + runs + metrics against Suva's labels

Datasets:
  calibration40  40 labelled rulings (Oct 2025 - Mar 2026), shown blind to Codex     (labelled)
  window         all 733 chamber 8/9 rulings Oct 2025 - Mar 2026                       (labelled)
  aprjun         177 subject-area candidates Apr - Jun 2026 (the target)                (no labels yet)

    python src/runs.py build                        # (re)build Apertus v1/v2 + Codex runs and the index
    python src/runs.py import FILE --id my-agent-v1 --dataset aprjun --model "Some model"
                                                     # add any other agent's JSONL (same row format)
    python src/runs.py index                        # recompute index.json only
"""
import argparse
import datetime as dt
import glob
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from eval_f2 import f_beta  # noqa: E402
from suva import examples, triage  # noqa: E402

RUNS = os.path.join(ROOT, "data", "runs")
DATASETS = {
    "calibration40": "40 labelled rulings, Oct 2025 – Mar 2026 (blind for every model)",
    "window": "All 733 social-insurance rulings, Oct 2025 – Mar 2026 (Suva's list = labels)",
    "aprjun": "177 candidates, Apr – Jun 2026 (target period, labels come from Suva after judging)",
}
NOW = lambda: dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731


def write_run(dataset, run_id, model, rows, notes=""):
    os.makedirs(os.path.join(RUNS, dataset), exist_ok=True)
    with open(os.path.join(RUNS, dataset, f"{run_id}.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"run": run_id, "model": model, "dataset": dataset, "created_at": NOW(), "notes": notes},
                           ensure_ascii=False) + "\n")
        for r in sorted(rows, key=lambda r: -(r["score"] or 0)):
            f.write(json.dumps({"docket": r["docket"], "score": r["score"], "relevant": bool(r["relevant"]),
                                "reason": (r.get("reason") or "")[:600]}, ensure_ascii=False) + "\n")
    print(f"  run {dataset}/{run_id}: {len(rows)} rulings, {sum(bool(r['relevant']) for r in rows)} relevant")


def read_run(path):
    meta, rows = {}, []
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        o = json.loads(line)
        if "docket" in o:
            rows.append(o)
        else:
            meta.update(o)
    return meta, rows


def db_rows(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    q = f"""SELECT j.docket, j.decision_date, j.subject, j.url, j.text, a.ai_score, a.title_de, a.explanation_de,
                   {'i.score' if 'iv_assessments' in tables else 'NULL'} AS iv,
                   {'p.score' if 'principle_assessments' in tables else 'NULL'} AS p,
                   {'p.reason_de' if 'principle_assessments' in tables else 'NULL'} AS p_reason,
                   {'f.main_score' if 'final_selection' in tables else 'NULL'} AS main_orig,
                   {'f.selected' if 'final_selection' in tables else 'NULL'} AS selected,
                   {'r.rescue' if 'rescue_assessments' in tables else 'NULL'} AS rescue,
                   {'r.norm' if 'rescue_assessments' in tables else 'NULL'} AS rescue_norm,
                   {'r.reason' if 'rescue_assessments' in tables else 'NULL'} AS rescue_reason
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            {'LEFT JOIN iv_assessments i ON i.slug = j.slug' if 'iv_assessments' in tables else ''}
            {'LEFT JOIN principle_assessments p ON p.slug = j.slug' if 'principle_assessments' in tables else ''}
            {'LEFT JOIN final_selection f ON f.slug = j.slug' if 'final_selection' in tables else ''}
            {'LEFT JOIN rescue_assessments r ON r.slug = j.slug' if 'rescue_assessments' in tables else ''}"""
    out = []
    for r in con.execute(q):
        d = dict(r)
        d.update(triage.classify({"subject": d["subject"], "text": d["text"]}))
        d.pop("text")
        d["main"] = d["main_orig"] if d["main_orig"] is not None else d["ai_score"]
        out.append(d)
    return out


def v1_selected(r):
    return (r["main"] or 0) >= 60 or ("invalidity" in r["areas"] and (r["iv"] or 0) >= 40)


def v2_selected(r):
    in_scope = "invalidity" in r["areas"] or ("accident" in r["areas"] and r["procedural"])
    return (r["p"] or 0) >= 60 if in_scope else (r["main"] or 0) >= 60


def write_dockets(dataset, rows, gt):
    meta = {r["docket"]: {"subject": r.get("subject") or "", "date": r.get("decision_date") or "",
                          "title": r.get("title_de") or "", "url": r.get("url") or "",
                          "suva": (r["docket"] in gt) if dataset != "aprjun" else None} for r in rows}
    os.makedirs(os.path.join(RUNS, dataset), exist_ok=True)
    json.dump(meta, open(os.path.join(RUNS, dataset, "_dockets.json"), "w"), ensure_ascii=False)


def build():
    gt = set(examples.load_ground_truth())
    win = [r for r in db_rows(os.path.join(ROOT, "data", "eval_window.sqlite")) if r["areas"]]
    apr = [r for r in db_rows(os.path.join(ROOT, "data", "aprjun.sqlite")) if r["areas"]]
    cal_ids = [json.loads(l)["docket"] for l in open(os.path.join(ROOT, "data/second_opinion/calibration_blind.jsonl"))]
    cal = [r for r in win if r["docket"] in set(cal_ids)]
    write_dockets("window", win, gt)
    write_dockets("calibration40", cal, gt)
    write_dockets("aprjun", apr, gt)

    def v1rows(rows):
        return [{"docket": r["docket"], "score": r["main"], "relevant": v1_selected(r),
                 "reason": r["explanation_de"]} for r in rows]

    def v2rows(rows):
        out = []
        for r in rows:
            in_scope = "invalidity" in r["areas"] or ("accident" in r["areas"] and r["procedural"])
            out.append({"docket": r["docket"], "score": r["p"] if in_scope and r["p"] is not None else r["main"],
                        "relevant": v2_selected(r), "reason": (r["p_reason"] if in_scope else r["explanation_de"])})
        return out

    v1_notes = "Earlier production (until Fri evening). Main triage score >= 60, plus IV second pass >= 40 for invalidity rulings (F2-tuned)."
    v2_notes = ("Experiment, rejected: 'general rule vs individual case' principle pass for invalidity and procedural "
                "rulings. Apertus labels almost everything a general rule.")
    for ds, rows in (("window", win), ("calibration40", cal)):
        write_run(ds, "apertus70b-v1", "Apertus v1.5 70B (CSCS/Keera)", v1rows(rows), v1_notes)
        if any(r["p"] is not None for r in rows):
            write_run(ds, "apertus70b-v2-principle", "Apertus v1.5 70B (CSCS/Keera)", v2rows(rows), v2_notes)
        if any(r["rescue"] is not None for r in rows):
            write_run(ds, "apertus70b-v3-atsg-rescue", "Apertus v1.5 70B (CSCS/Keera)",
                      [{"docket": r["docket"], "score": 60 if (v1_selected(r) or r["rescue"]) else r["main"],
                        "relevant": v1_selected(r) or bool(r["rescue"]),
                        "reason": (f"ATSG-Rescue ({r['rescue_norm']}): {r['rescue_reason']}" if r["rescue"] and not v1_selected(r)
                                   else r["explanation_de"])} for r in rows],
                      "Experiment, rejected: v1 plus an 'ATSG rescue' pass over rejected candidates (lesson from Codex: "
                      "ATSG rules bind IV and UVG alike; quote required). Rescued 110, only 4 were Suva picks.")
    write_run("aprjun", "apertus70b-v1", "Apertus v1.5 70B (CSCS/Keera)",
              [{"docket": r["docket"], "score": r["main"], "relevant": v1_selected(r), "reason": r["explanation_de"]}
               for r in apr], v1_notes)
    if any(r["rescue"] is not None for r in apr):
        write_run("aprjun", "apertus70b-v3-atsg-rescue", "Apertus v1.5 70B (CSCS/Keera)",
                  [{"docket": r["docket"], "score": 60 if (v1_selected(r) or r["rescue"]) else r["main"],
                    "relevant": v1_selected(r) or bool(r["rescue"]),
                    "reason": (f"ATSG-Rescue ({r['rescue_norm']}): {r['rescue_reason']}"
                               if r["rescue"] and not v1_selected(r) else r["explanation_de"])} for r in apr],
                  "Experiment, not submitted: v1 + ATSG rescue. Catches 4 of the 5 Codex-only rulings but adds 59 in total; "
                  "on the labelled window only ~4 % of rescued rulings were Suva picks (F2 0.736 -> 0.598).")
    write_run("aprjun", "apertus70b-v4-tiers-ranked", "Apertus v1.5 70B (CSCS/Keera)",
              [{"docket": r["docket"], "score": r["ai_score"], "relevant": bool(r["selected"]),
                "reason": r["explanation_de"]} for r in apr],
              "PRODUCTION (submitted): Tier 1 + Grenzfälle (adapted pass 4), Tier 1 ordered by the LEARNED ranking "
              "(weighting of Apertus' judgements fitted on Suva's Q4/Q1 list; src/learn_ranking.py), Grenzfälle below.")
    sh = os.path.join(ROOT, "data", "aprjun.sqlite")
    con = sqlite3.connect(sh)
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='rankings_shadow'").fetchone():
        final = dict(con.execute("SELECT j.docket, s.final FROM rankings_shadow s JOIN judgements j ON j.slug = s.slug").fetchall())
        write_run("aprjun", "apertus70b-shadow-rank", "Apertus v1.5 70B (CSCS/Keera)",
                  [{"docket": r["docket"], "score": round(final[r["docket"]], 1) if r["docket"] in final else None,
                    "relevant": bool(r["selected"]), "reason": r["explanation_de"]} for r in apr],
                  "EXPERIMENT (not live): same list as production, order from the shadow ranking (sub-scores + listwise top 15).")
    for ds, path in (("calibration40", "codex_calibration.jsonl"), ("aprjun", "codex_aprjun.jsonl")):
        p = os.path.join(ROOT, "data", "second_opinion", path)
        if os.path.exists(p):
            imp(p, "codex-gpt6", ds, None, "Development reference only (closed model, not allowed at runtime). Blind.")
    for agent in ("gem", "misty", "muse", "clau"):
        for ds, suffix in (("calibration40", "calibration"), ("aprjun", "aprjun")):
            p = os.path.join(ROOT, "data", "second_opinion", f"{agent}_{suffix}.jsonl")
            if os.path.exists(p):
                imp(p, agent, ds, None, "Fleet agent, blind second opinion (development reference only).")
    try:  # weighted consensus of the second-opinion agents (src/consensus.py), refreshed on every build
        import consensus
        consensus.main()
    except Exception as e:  # noqa: BLE001
        print("consensus skipped:", e)
    index()


def imp(path, run_id, dataset, model, notes=""):
    meta, rows = read_run(path)
    rows = [{"docket": r["docket"], "score": r.get("score"), "relevant": r.get("relevant", (r.get("score") or 0) >= 50),
             "reason": r.get("reason", "")} for r in rows]
    write_run(dataset, run_id, model or meta.get("model") or run_id, rows, notes or meta.get("notes", ""))


def metrics(rows, labels):
    pos = {d for d, v in labels.items() if v}
    ids = {r["docket"] for r in rows} & set(labels)
    sel = {r["docket"] for r in rows if r["relevant"] and r["docket"] in ids}
    pos &= ids
    tp = len(sel & pos)
    p = tp / len(sel) if sel else 0.0
    rc = tp / len(pos) if pos else 0.0
    sc = {r["docket"]: r["score"] or 0 for r in rows if r["docket"] in ids}
    P = [sc[d] for d in ids if d in pos]
    N = [sc[d] for d in ids if d not in pos]
    auc = (sum((a > b) + 0.5 * (a == b) for a in P for b in N) / (len(P) * len(N))) if P and N else None
    return {"rulings": len(ids), "positives": len(pos), "listed": len(sel), "hits": tp, "recall": round(rc, 3),
            "precision": round(p, 3), "f2": round(f_beta(p, rc), 3), "auc": round(auc, 3) if auc is not None else None}


def index():
    out = {"generated_at": NOW(), "datasets": [], "runs": []}
    for ds, label in DATASETS.items():
        dpath = os.path.join(RUNS, ds, "_dockets.json")
        if not os.path.exists(dpath):
            continue
        dockets = json.load(open(dpath))
        labels = {d: m["suva"] for d, m in dockets.items() if m.get("suva") is not None}
        out["datasets"].append({"id": ds, "label": label, "rulings": len(dockets), "labelled": bool(labels),
                                "positives": sum(labels.values())})
        for f in sorted(glob.glob(os.path.join(RUNS, ds, "*.jsonl"))):
            meta, rows = read_run(f)
            entry = {"id": meta.get("run"), "dataset": ds, "model": meta.get("model"), "notes": meta.get("notes", ""),
                     "created_at": meta.get("created_at"), "rulings": len(rows),
                     "listed": sum(bool(r["relevant"]) for r in rows)}
            if labels:
                entry["metrics"] = metrics(rows, labels)
            out["runs"].append(entry)
    json.dump(out, open(os.path.join(RUNS, "index.json"), "w"), ensure_ascii=False, indent=1)
    for r in out["runs"]:
        m = r.get("metrics") or {}
        print(f"  {r['dataset']:14} {r['id']:26} listed {r['listed']:4}  F2 {m.get('f2', '–')}  AUC {m.get('auc', '–')}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("index")
    i = sub.add_parser("import")
    i.add_argument("file")
    i.add_argument("--id", required=True)
    i.add_argument("--dataset", required=True, choices=list(DATASETS))
    i.add_argument("--model", default=None)
    i.add_argument("--notes", default="")
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    elif a.cmd == "index":
        index()
    else:
        imp(a.file, a.id, a.dataset, a.model, a.notes)
        index()


if __name__ == "__main__":
    main()
