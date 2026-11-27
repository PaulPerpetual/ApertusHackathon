"""Weighted consensus ranking of the second-opinion agents (reference for analysing Apertus; never submitted).

Formula (agreed with Miguel, Fri 27 Nov):
  1. Ranks, not raw scores: each agent's scores -> percentile rank p in [0, 1] (1 = its most important ruling),
     ties get the average rank. Removes the agents' different score scales.
  2. Weight per agent  w = prior x skill
       prior: Clau, Codex, Gem = 1.0; Misty, Muse = 0.5
       skill: 2 x (AUC - 0.5) on the 40 blind labelled calibration rulings (Suva's picks known); <= 0 -> weight 0.
              If an agent has no calibration file, skill = 0.5 (neutral).
  3. Consensus  c(d) = sum_i w_i p_i(d) / sum_i w_i  over agents that scored d.
  4. Disagreement  s(d) = weighted standard deviation of p_i(d).
  5. Relevance consensus: weighted share of agents saying relevant; >= 0.5 -> relevant.
Apertus is NOT part of the consensus: the consensus is the yardstick Apertus is measured against.

Writes runs 'consensus-weighted' for calibration40 and aprjun (data/runs/...), and data/consensus_weights.json.
    python src/consensus.py
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from runs import RUNS, read_run, write_run  # noqa: E402

PRIOR = {"clau": 1.0, "codex-gpt6": 1.0, "gem": 1.0, "misty": 0.5, "muse": 0.5}


def percentiles(rows):
    """docket -> percentile rank in [0, 1], 1 = highest score; ties share the average rank."""
    items = sorted(((r["score"] if r["score"] is not None else -1), r["docket"]) for r in rows)
    n = len(items)
    out, i = {}, 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][0] == items[i][0]:
            j += 1
        avg = (i + j) / 2
        for k in range(i, j + 1):
            out[items[k][1]] = avg / (n - 1) if n > 1 else 1.0
        i = j + 1
    return out


def auc(rows, labels):
    s = {r["docket"]: (r["score"] if r["score"] is not None else -1) for r in rows if r["docket"] in labels}
    pos = [v for d, v in s.items() if labels[d]]
    neg = [v for d, v in s.items() if not labels[d]]
    if not pos or not neg:
        return None
    return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))


def main():
    dockets = json.load(open(os.path.join(RUNS, "calibration40", "_dockets.json")))
    labels = {d: m["suva"] for d, m in dockets.items() if m.get("suva") is not None}
    weights = {}
    for agent, prior in PRIOR.items():
        cal = os.path.join(RUNS, "calibration40", f"{agent}.jsonl")
        if os.path.exists(cal):
            a = auc(read_run(cal)[1], labels)
            skill = max(0.0, 2 * (a - 0.5)) if a is not None else 0.5
            weights[agent] = {"prior": prior, "auc": round(a, 3) if a is not None else None,
                              "skill": round(skill, 3), "weight": round(prior * skill, 3)}
        elif os.path.exists(os.path.join(RUNS, "aprjun", f"{agent}.jsonl")):
            weights[agent] = {"prior": prior, "auc": None, "skill": 0.5, "weight": round(prior * 0.5, 3)}
    json.dump(weights, open(os.path.join(ROOT, "data", "consensus_weights.json"), "w"), indent=1)
    print("weights:", {a: w["weight"] for a, w in weights.items()})
    for ds in ("calibration40", "aprjun"):
        per = {}
        for agent, w in weights.items():
            f = os.path.join(RUNS, ds, f"{agent}.jsonl")
            if w["weight"] > 0 and os.path.exists(f):
                rows = read_run(f)[1]
                per[agent] = (w["weight"], percentiles(rows), {r["docket"]: bool(r["relevant"]) for r in rows})
        if not per:
            continue
        all_d = set().union(*(p[1].keys() for p in per.values()))
        out = []
        for d in all_d:
            vals = [(w, p[d], rel.get(d, False)) for w, p, rel in per.values() if d in p]
            ws = sum(w for w, _, _ in vals)
            c = sum(w * p for w, p, _ in vals) / ws
            sd = math.sqrt(sum(w * (p - c) ** 2 for w, p, _ in vals) / ws)
            vote = sum(w for w, _, r in vals if r) / ws
            out.append({"docket": d, "score": round(100 * c, 1), "relevant": vote >= 0.5,
                        "reason": f"Konsens aus {len(vals)} Agent(en) ({', '.join(sorted(a for a in per if d in per[a][1]))}); "
                                  f"Streuung {sd:.2f}; Relevanz-Stimmen {vote:.0%}"})
        notes = ("Weighted consensus of the second-opinion agents (reference only, not submitted). Percentile ranks, "
                 "weight = prior (Clau/Codex/Gem 1.0, Misty/Muse 0.5) x skill (2*(AUC-0.5) on calibration40). Weights: " +
                 ", ".join(f"{a} {w['weight']}" for a, w in weights.items()))
        write_run(ds, "consensus-weighted", "Weighted consensus (" + ", ".join(per) + ")", out, notes)


if __name__ == "__main__":
    main()
