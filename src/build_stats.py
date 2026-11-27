"""Build data/stats.json for the stats page (/stats): model comparison, F2 curves, April-June overview.

Inputs (all local; whatever exists is used):
  data/eval_window.sqlite                      Apertus triage on the labelled window (Oct 2025 - Mar 2026)
  data/aprjun.sqlite                           Apertus triage on the target period (Apr - Jun 2026)
  data/second_opinion/codex_calibration.jsonl  Codex, blind, 40 labelled rulings (optional)
  data/second_opinion/codex_aprjun.jsonl       Codex, blind, April-June candidates (optional)
  judgements/BG_Urteile_2025_Q4_2026_Q1.xlsx   Suva's picks (ground truth for the window)

    python src/build_stats.py            -> data/stats.json
"""
import collections
import datetime as dt
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from eval_f2 import f_beta  # noqa: E402
from suva import examples, triage  # noqa: E402

D = lambda *p: os.path.join(ROOT, "data", *p)  # noqa: E731


def rows_of(db):
    if not os.path.exists(db):
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    has_iv = con.execute("SELECT 1 FROM sqlite_master WHERE name='iv_assessments'").fetchone()
    has_fin = con.execute("SELECT 1 FROM sqlite_master WHERE name='final_selection'").fetchone()
    q = f"""SELECT j.slug, j.docket, j.decision_date, j.subject, j.text, a.ai_score, a.model,
                   {'i.score' if has_iv else 'NULL'} AS iv,
                   {'f.main_score' if has_fin else 'NULL'} AS main_orig,
                   {'f.selected' if has_fin else 'NULL'} AS selected,
                   (SELECT COUNT(*) FROM summaries s WHERE s.slug = j.slug) AS n_sum
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            {'LEFT JOIN iv_assessments i ON i.slug = j.slug' if has_iv else ''}
            {'LEFT JOIN final_selection f ON f.slug = j.slug' if has_fin else ''}"""
    out = []
    for r in con.execute(q):
        d = dict(r)
        d.update(triage.classify({"subject": d["subject"], "text": d["text"]}))
        d.pop("text")
        d["main"] = d["main_orig"] if d["main_orig"] is not None else d["ai_score"]
        out.append(d)
    return out


def metrics(selected, positives):
    sel = set(selected)
    tp = len(sel & positives)
    p = tp / len(sel) if sel else 0.0
    r = tp / len(positives) if positives else 0.0
    return {"listed": len(sel), "hits": tp, "recall": round(r, 3), "precision": round(p, 3), "f2": round(f_beta(p, r), 3)}


def auc(pos, neg):
    if not pos or not neg:
        return None
    return round(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)), 3)


def read_jsonl(path):
    if not os.path.exists(path):
        return None, {}
    model, out = None, {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if "docket" not in o:
            model = o.get("model", model)
            continue
        out[o["docket"]] = o
    return model, out


def main():
    gt = set(examples.load_ground_truth())
    stats = {"generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

    # ---------------------------------------------------------------- labelled window
    w = rows_of(D("eval_window.sqlite"))
    if w:
        pos = {r["docket"] for r in w if r["docket"] in gt}
        curve = []
        for t in range(0, 101, 5):
            m = metrics([r["docket"] for r in w if (r["main"] or 0) >= t], pos)
            curve.append({"cutoff": t, **m})
        area = [r["docket"] for r in w if r["areas"]]
        acc = [r["docket"] for r in w if "accident" in r["areas"] and not r["procedural"]]
        main60 = [r["docket"] for r in w if (r["main"] or 0) >= 60]
        union = [r["docket"] for r in w if (r["main"] or 0) >= 60 or
                 ("invalidity" in r["areas"] and r["iv"] is not None and r["iv"] >= 40)]
        iv = [r for r in w if "invalidity" in r["areas"]]
        comparison = [
            {"name": "Baseline: all subject-area candidates", "kind": "rule", **metrics(area, pos)},
            {"name": "Baseline: accident insurance, on the merits", "kind": "rule", **metrics(acc, pos)},
            {"name": "Apertus 70B, score >= 60", "kind": "apertus", **metrics(main60, pos)},
            {"name": "Apertus 70B + IV second pass (selected rule)", "kind": "apertus", **metrics(union, pos)},
        ]
        by_area = {}
        for a in ("accident", "invalidity", "daily_allowance"):
            g = [r for r in w if a in r["areas"]]
            by_area[a] = {"rulings": len(g), "suva_picked": sum(r["docket"] in gt for r in g),
                          **{k: v for k, v in metrics([r["docket"] for r in g if r["docket"] in set(union)],
                                                       {r["docket"] for r in g if r["docket"] in gt}).items()}}
        stats["window"] = {
            "label": "Oct 2025 – Mar 2026 (Suva's list = ground truth)",
            "rulings": len(w), "suva_positives": len(pos), "candidates": len(area),
            "curve": curve, "comparison": comparison, "by_area": by_area,
            "iv_auc": {"main_prompt": auc([r["main"] for r in iv if r["docket"] in gt],
                                          [r["main"] for r in iv if r["docket"] not in gt]),
                       "iv_second_pass": auc([r["iv"] for r in iv if r["docket"] in gt and r["iv"] is not None],
                                             [r["iv"] for r in iv if r["docket"] not in gt and r["iv"] is not None])},
        }
        # Codex on the 40 blind calibration rulings vs Apertus on the same 40
        cmodel, cal = read_jsonl(D("second_opinion", "codex_calibration.jsonl"))
        if cal:
            ids = set(cal)
            wpos = {d for d in ids if d in gt}
            byd = {r["docket"]: r for r in w}
            apx = [d for d in ids if d in set(union)]
            cx = [d for d, o in cal.items() if o.get("relevant")]
            stats["window"]["calibration40"] = {
                "codex_model": cmodel or "Codex",
                "apertus": metrics(apx, wpos), "codex": metrics(cx, wpos),
                "agreement": round(sum((d in set(apx)) == (d in set(cx)) for d in ids) / len(ids), 3),
                "auc_codex": auc([cal[d]["score"] for d in ids if d in gt], [cal[d]["score"] for d in ids if d not in gt]),
                "auc_apertus": auc([byd[d]["main"] for d in ids if d in gt and d in byd],
                                   [byd[d]["main"] for d in ids if d not in gt and d in byd]),
            }

    # ---------------------------------------------------------------- April - June
    p = rows_of(D("aprjun.sqlite"))
    if p:
        cand = [r for r in p if r["areas"]]
        sel = [r for r in p if r["selected"]] if any(r["selected"] is not None for r in p) else \
              [r for r in p if (r["ai_score"] or 0) >= 60]
        months = collections.OrderedDict((m, {"candidates": 0, "selected": 0, "summarised": 0})
                                         for m in ("2026-04", "2026-05", "2026-06"))
        for r in cand:
            m = (r["decision_date"] or "")[:7]
            if m in months:
                months[m]["candidates"] += 1
        for r in sel:
            m = (r["decision_date"] or "")[:7]
            if m in months:
                months[m]["selected"] += 1
                months[m]["summarised"] += int(r["n_sum"] > 0)
        hist = collections.Counter((r["ai_score"] or 0) // 10 * 10 for r in cand)
        stats["aprjun"] = {
            "label": "Apr – Jun 2026 (target period, no labels)",
            "crawled": len(p), "candidates": len(cand), "selected": len(sel),
            "selected_by_area": dict(collections.Counter(a for r in sel for a in (r["areas"] or ["none"]))),
            "summarised": sum(r["n_sum"] > 0 for r in sel),
            "months": months,
            "score_hist": [{"bin": b, "count": hist.get(b, 0)} for b in range(0, 101, 10)],
        }
        cmodel, cx = read_jsonl(D("second_opinion", "codex_aprjun.jsonl"))
        if cx:
            sel_set = {r["docket"] for r in sel}
            cand_set = {r["docket"] for r in cand}
            c_rel = {d for d, o in cx.items() if o.get("relevant")}
            stats["aprjun"]["codex"] = {
                "codex_model": cmodel or "Codex", "codex_listed": len(c_rel & cand_set),
                "both": len(sel_set & c_rel), "only_apertus": len(sel_set - c_rel), "only_codex": len((c_rel & cand_set) - sel_set),
                "only_codex_dockets": sorted((c_rel & cand_set) - sel_set),
                "only_apertus_dockets": sorted(sel_set - c_rel),
            }
    json.dump(stats, open(D("stats.json"), "w"), ensure_ascii=False, indent=1)
    print("wrote", D("stats.json"), "| sections:", [k for k in stats if k != "generated_at"])


if __name__ == "__main__":
    main()
