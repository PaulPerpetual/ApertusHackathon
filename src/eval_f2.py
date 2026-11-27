"""Evaluate triage the way Suva scores the hit list: Recall and F2 against Suva's relevant set.

Suva's slide: "deliver the list in style 8C_691/2024, 9C_612/2025 ...; we calculate Recall and F2".
F2 = 5PR / (4P + R) weighs recall 4x more than precision, so the best cutoff is generous.

Ground truth: judgements/BG_Urteile_2025_Q4_2026_Q1.xlsx (Suva's Q4-2025/Q1-2026 picks).
Run against a DB triaged on the labelled window (data/period/2025-10-01_2026-03-31_ch89):

    python src/eval_f2.py data/eval_window.sqlite [--errors]
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from suva import examples, triage  # noqa: E402


def f_beta(p, r, beta=2.0):
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r) if p + r else 0.0


def load(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT j.docket, j.subject, j.division, j.text, a.ai_score, a.prefilter_score, a.model,
                                 a.explanation_de FROM judgements j JOIN assessments a ON a.slug = j.slug""").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        c = triage.classify({"subject": d["subject"], "text": d["text"]})
        d.update(c)
        d.pop("text")
        out.append(d)
    return out


def curve(rows, gt, score_key="ai_score"):
    pos = {r["docket"] for r in rows if r["docket"] in gt}
    res = []
    for t in sorted({r[score_key] for r in rows}, reverse=True):
        sel = {r["docket"] for r in rows if r[score_key] >= t}
        tp = len(sel & pos)
        p = tp / len(sel) if sel else 0.0
        r = tp / len(pos) if pos else 0.0
        res.append({"t": t, "n": len(sel), "tp": tp, "P": p, "R": r, "F2": f_beta(p, r)})
    return res, len(pos)


def _table(con, name):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def variants(db, rows, gt, npos):
    """Production rule (main >= 60 OR IV pass >= 40) vs. the same plus leading-case signals and the recall pass."""
    import json
    from suva import recall_pass
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    main = {r["docket"]: r["ai_score"] or 0 for r in rows}
    if _table(con, "final_selection"):  # finalize.py lifts promoted IV rulings to 60; use the original main score
        for r in con.execute("SELECT j.docket, f.main_score FROM final_selection f JOIN judgements j ON j.slug = f.slug"):
            if r["main_score"] is not None:
                main[r["docket"]] = r["main_score"]
    iv = {r["docket"]: r["score"] for r in con.execute(
        "SELECT j.docket, i.score FROM iv_assessments i JOIN judgements j ON j.slug = i.slug")} if _table(con, "iv_assessments") else {}
    rec, lead = {}, {}
    if _table(con, "recall_assessments"):
        for r in con.execute("SELECT j.docket, r.score, r.leading FROM recall_assessments r JOIN judgements j ON j.slug = r.slug"):
            rec[r["docket"]] = r["score"]
            lead[r["docket"]] = json.loads(r["leading"] or "[]")
    else:
        print("\n(no recall_assessments table: run src/run_recall_pass.py first)")
    pos = {d for d in main if d in gt}

    def report(name, sel):
        tp = len(sel & pos)
        p, r = (tp / len(sel) if sel else 0.0), (tp / len(pos) if pos else 0.0)
        print(f"  {name:44} {len(sel):5} {tp:5}  {r:6.0%}  {p:8.0%}  {f_beta(p, r):.3f}")

    print(f"\nVARIANTS ({npos} on Suva's list; {sum(1 for v in lead.values() if v)} rulings with leading-case signals, "
          f"{sum(1 for v in rec.values() if v is not None)} re-assessed by the recall pass)")
    print(f"  {'rule':44} listed  hits  recall  precision   F2")
    for cut in (60, 50, 40):
        base = {d for d, s in main.items() if s >= cut} | {d for d, s in iv.items() if (s or 0) >= 40}
        report(f"main >= {cut} or IV pass >= 40", base)
        report(f"  + leading-case signals", base | {d for d, v in lead.items() if v})
        report(f"  + recall pass >= {cut}", base | {d for d, s in rec.items() if (s or 0) >= cut})
        both = base | {d for d in main if recall_pass.combined(main[d], rec.get(d), lead.get(d) or ()) >= cut}
        report(f"  + both", both)
    missed = sorted(pos - {d for d in main if recall_pass.combined(main[d], rec.get(d), lead.get(d) or ()) >= 50}
                    - {d for d, s in iv.items() if (s or 0) >= 40})
    print(f"\n  still missed at 50 with both: {', '.join(missed) or '-'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--errors", action="store_true", help="list misses and false alarms at the best cutoff")
    ap.add_argument("--variants", action="store_true",
                    help="compare production selection with the recall pass (run_recall_pass.py) at several cutoffs")
    a = ap.parse_args()
    gt = examples.load_ground_truth()
    rows = load(a.db)
    res, npos = curve(rows, gt)
    print(f"{len(rows)} rulings, {npos} on Suva's list\n")
    print(" cutoff  listed  hits  recall  precision   F2")
    for x in res:
        if x["n"] <= 400:
            print(f"  >={x['t']:<4} {x['n']:6} {x['tp']:5}  {x['R']:6.0%}  {x['P']:8.0%}  {x['F2']:.3f}")
    best = max(res, key=lambda x: x["F2"])
    print(f"\nbest F2 {best['F2']:.3f} at score >= {best['t']} ({best['n']} listed, recall {best['R']:.0%}, "
          f"precision {best['P']:.0%})")
    # baselines
    area = [r for r in rows if r["areas"]]
    tp = sum(r["docket"] in gt for r in area)
    p, rr = tp / max(len(area), 1), tp / max(npos, 1)
    print(f"baseline 'all subject-area candidates': {len(area)} listed, recall {rr:.0%}, precision {p:.0%}, "
          f"F2 {f_beta(p, rr):.3f}")
    acc = [r for r in rows if "accident" in r["areas"] and not r["procedural"]]
    tp = sum(r["docket"] in gt for r in acc)
    p, rr = tp / max(len(acc), 1), tp / max(npos, 1)
    print(f"baseline 'accident, on the merits':     {len(acc)} listed, recall {rr:.0%}, precision {p:.0%}, "
          f"F2 {f_beta(p, rr):.3f}")
    if a.variants:
        variants(a.db, rows, gt, npos)
    if a.errors:
        t = best["t"]
        print(f"\nMISSES (on Suva's list, score < {t}):")
        for r in sorted(rows, key=lambda r: -r["ai_score"]):
            if r["docket"] in gt and r["ai_score"] < t:
                print(f"  {r['ai_score']:3} {r['docket']:13} {','.join(r['areas']) or '-':10} {r['subject'][:70]}\n"
                      f"      Apertus: {(r['explanation_de'] or '')[:220]}")
        print(f"\nFALSE ALARMS (not on Suva's list, score >= {t}), highest first:")
        for r in sorted(rows, key=lambda r: -r["ai_score"]):
            if r["docket"] not in gt and r["ai_score"] >= t:
                print(f"  {r['ai_score']:3} {r['docket']:13} {','.join(r['areas']) or '-':10} {r['subject'][:70]}")


if __name__ == "__main__":
    main()
