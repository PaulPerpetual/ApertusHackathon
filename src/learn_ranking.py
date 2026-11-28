"""Learned ranking (experiment): weight Apertus' own judgements by what predicts Suva's choices.

Every feature is an Apertus output (triage score, IV pass, pass-5 importance, shadow sub-scores K1-K5/A) or a fact
from the ruling (Suva party, procedural, subject area, five-judge panel). A small L2 logistic regression is fitted on
the labelled window (Oct 2025 - Mar 2026, Suva's yes/no list) over the rulings that correspond to our Tier 1 (the
ones that form the top of the list). Evaluated by repeated stratified cross-validation (precision@5/10/30 within each
held-out fold, scaled to list size) against the current ranking (pass 5).

    python src/learn_ranking.py               # evaluate + print weights
    python src/learn_ranking.py --apply       # also write rankings_learned to data/aprjun.sqlite (live list untouched)
"""
import argparse
import json
import os
import re
import sqlite3
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import examples, triage  # noqa: E402

FEATURES = ["main", "importance", "K1", "K2", "K3", "K4", "K5", "A", "iv", "suva_party", "procedural", "accident", "five_judges"]


def five_judges(text):
    m = re.search(r"(Besetzung|Composition|Composizione)(.{0,600}?)(Gerichtsschreiber|Greffi|Cancellier)", (text or "")[:6000], re.S)
    if not m:
        return 0
    names = re.findall(r"\b[A-ZÄÖÜ][a-zäöüéèà\-]+(?=,|\s+und\s|\s+et\s|\s+e\s|\.)", m.group(2))
    return int(len(names) >= 5)


def load(db, only_list=True):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    t = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    acols = {r[1] for r in con.execute("PRAGMA table_info(assessments)")}
    rows = []
    for r in con.execute(f"""SELECT j.slug, j.docket, j.subject, j.text,
            {'COALESCE(f.main_score, a.ai_score)' if 'final_selection' in t else 'a.ai_score'} AS main, a.suva_party,
            {'a.tier' if 'tier' in acols else 'NULL'} AS tier, i.score AS iv, rk.importance, sh.criteria
            FROM judgements j JOIN assessments a ON a.slug = j.slug
            {'LEFT JOIN final_selection f ON f.slug = j.slug' if 'final_selection' in t else ''}
            LEFT JOIN iv_assessments i ON i.slug = j.slug
            JOIN rankings rk ON rk.slug = j.slug JOIN rankings_shadow sh ON sh.slug = j.slug"""):
        d = dict(r)
        c = triage.classify({"subject": d["subject"], "text": d["text"]})
        if only_list and d["tier"] is not None and d["tier"] != 1:
            continue  # rank Tier 1 (Grenzfälle stay below, unchanged)
        k = json.loads(d["criteria"] or "{}")
        d.update({n: float(k.get(n, 0)) for n in ("K1", "K2", "K3", "K4", "K5", "A")})
        d.update({"iv": float(d["iv"] or 0), "suva_party": float(d["suva_party"] or 0), "procedural": float(c["procedural"]),
                  "accident": float("accident" in c["areas"]), "five_judges": float(five_judges(d["text"])),
                  "main": float(d["main"] or 0), "importance": float(d["importance"] or 0)})
        d.pop("text")
        rows.append(d)
    return rows


def prec_at(scores, y, k):
    order = np.argsort(-scores, kind="stable")
    return float(np.mean(y[order[:k]])) if len(y) >= k else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--C", type=float, default=0.3)
    a = ap.parse_args()
    gt = set(examples.load_ground_truth())
    w = load(os.path.join(ROOT, "data", "eval_window.sqlite"), only_list=False)
    X = np.array([[r[f] for f in FEATURES] for r in w])
    y = np.array([int(r["docket"] in gt) for r in w])
    print(f"window: {len(w)} rulings (our Tier-1 analogue), {y.sum()} on Suva's list")
    base = np.array([r["importance"] + 0.01 * r["main"] for r in w])  # current ranking: pass 5 (ties by triage)
    rng = np.random.default_rng(0)
    res = {"current (pass 5)": {5: [], 10: []}, "learned": {5: [], 10: []}, "triage only": {5: [], 10: []}}
    cv = RepeatedStratifiedKFold(n_splits=3, n_repeats=30, random_state=0)
    for tr, te in cv.split(X, y):
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(C=a.C, max_iter=2000).fit(sc.transform(X[tr]), y[tr])
        p = m.predict_proba(sc.transform(X[te]))[:, 1]
        jitter = rng.random(len(te)) * 1e-6
        for k in (5, 10):
            res["learned"][k].append(prec_at(p + jitter, y[te], k))
            res["current (pass 5)"][k].append(prec_at(base[te] + jitter, y[te], k))
            res["triage only"][k].append(prec_at(X[te][:, 0] + jitter, y[te], k))
    print("held-out folds of ~34 rulings (3-fold x 30 repeats):")
    for name, r in res.items():
        print(f"  {name:18} precision@5 {np.nanmean(r[5]):4.0%}   @10 {np.nanmean(r[10]):4.0%}")
    sc = StandardScaler().fit(X)
    m = LogisticRegression(C=a.C, max_iter=2000).fit(sc.transform(X), y)
    print("weights (standardised; + = more likely Suva pick):")
    for f, c in sorted(zip(FEATURES, m.coef_[0]), key=lambda x: -abs(x[1])):
        print(f"  {f:12} {c:+.2f}")
    if a.apply:
        db = os.path.join(ROOT, "data", "aprjun.sqlite")
        q = load(db, only_list=True)
        Xq = np.array([[r[f] for f in FEATURES] for r in q])
        pq = m.predict_proba(sc.transform(Xq))[:, 1]
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE IF NOT EXISTS rankings_learned (slug TEXT PRIMARY KEY, p REAL)")
        con.execute("DELETE FROM rankings_learned")
        con.executemany("INSERT INTO rankings_learned VALUES (?,?)", [(r["slug"], float(p)) for r, p in zip(q, pq)])
        con.commit()
        top = sorted(zip(q, pq), key=lambda x: -x[1])[:10]
        print("Apr-Jun Tier 1, learned top 10:", [(r["docket"], round(float(p), 2)) for r, p in top])
        json.dump({"features": FEATURES, "coef": m.coef_[0].tolist(), "intercept": float(m.intercept_[0]),
                   "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(), "C": a.C},
                  open(os.path.join(ROOT, "data", "learned_ranking_model.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
