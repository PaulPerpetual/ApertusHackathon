"""Side-by-side data for the Examples page (/examples): Suva's expert summaries vs ours, same rulings.

Our pipeline processes Suva's example rulings from scratch (data/examples_eval.sqlite: triage, Begründung,
summaries). Suva's own summary of a ruling is never shown to the model for that ruling (pipeline rule),
so this is a blind comparison.

Metrics per ruling and language (indicators only, reading is what counts):
  words, consideration references "(E. x)" / "(consid. x)", content-word overlap with Suva (F1).

    python src/build_examples_compare.py      -> data/examples_compare.json
"""
import json
import os
import re
import sqlite3
import sys
from statistics import median

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from suva import erwaegungen, examples  # noqa: E402

STOP = set("""der die das und des den dem ein eine einer eines nicht mit von zu zur zum auf für ist sich als auch bei aus wird
werden wurde wurden sind hat haben oder dass vom im in an es sie er seine ihre kann nach durch noch nur wie so diese dieser
le la les des une est que qui dans pour par sur pas aux ses son sont été être ont avec cette il elle du de et en un au ne se""".split())
REFS = re.compile(r"\((?:E\.|Erw\.|consid\.)\s*[0-9][^)]*\)")


def words(t):
    return [w for w in re.findall(r"[a-zäöüéèàçâêîôû]{3,}", (t or "").lower()) if w not in STOP]


def overlap(a, b):
    """Content-word F1 between two texts (multiset)."""
    from collections import Counter
    ca, cb = Counter(words(a)), Counter(words(b))
    common = sum((ca & cb).values())
    if not common:
        return 0.0
    p, r = common / sum(ca.values()), common / sum(cb.values())
    return round(2 * p * r / (p + r), 3)


def main():
    db = os.path.join(ROOT, "data", "examples_eval.sqlite")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    ours = {}
    for r in con.execute("""SELECT j.slug, j.docket, j.decision_date, j.language, j.subject, j.url, j.text,
                                   a.ai_score, a.title_de, a.title_fr, a.explanation_de, a.explanation_fr, a.tags, a.tags_fr,
                                   e.de AS ex_de, e.fr AS ex_fr
                            FROM judgements j JOIN assessments a ON a.slug = j.slug
                            LEFT JOIN explanations e ON e.slug = j.slug"""):
        d = dict(r)
        d["summaries"] = {s["lang"]: s["text"] for s in con.execute("SELECT lang, text FROM summaries WHERE slug=?", (d["slug"],))}
        ours[d["docket"]] = d
    items = []
    for ex in examples.load_examples():
        o = ours.get(ex["docket"])
        if not o or not o["summaries"]:
            continue
        valid = erwaegungen.numbers(o["text"])
        it = {"docket": ex["docket"], "date": o["decision_date"], "language": o["language"], "subject": o["subject"],
              "url": ex.get("url") or o["url"], "score": o["ai_score"],
              "title": {"de": o["title_de"], "fr": o["title_fr"]},
              "begruendung": {"de": o["ex_de"] or o["explanation_de"], "fr": o["ex_fr"] or o["explanation_fr"]},
              "tags": {"de": json.loads(o["tags"] or "[]"), "fr": json.loads(o["tags_fr"] or "[]")},
              "suva": {"de": ex["de"], "fr": ex["fr"], "author": ex.get("author", "")},
              "ours": {"de": o["summaries"].get("de", ""), "fr": o["summaries"].get("fr", "")},
              "considerations": valid, "metrics": {}}
        for lang in ("de", "fr"):
            s, a = it["suva"][lang], it["ours"][lang]
            it["metrics"][lang] = {"words_suva": len(s.split()), "words_ours": len(a.split()),
                                   "refs_suva": len(REFS.findall(s)), "refs_ours": len(REFS.findall(a)),
                                   "overlap": overlap(a, s)}
        items.append(it)
    items.sort(key=lambda x: x["date"] or "", reverse=True)

    def agg(lang, k):
        v = [i["metrics"][lang][k] for i in items]
        return round(median(v), 3) if v else None
    out = {"n": len(items),
           "summary": {lang: {k: agg(lang, k) for k in ("words_suva", "words_ours", "refs_suva", "refs_ours", "overlap")}
                       for lang in ("de", "fr")},
           "flagged_relevant": sum((i["score"] or 0) >= 60 for i in items),
           "items": items}
    for i in items:
        i.pop("considerations")
    json.dump(out, open(os.path.join(ROOT, "data", "examples_compare.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{len(items)} rulings -> data/examples_compare.json; medians: {out['summary']}; "
          f"Apertus scored {out['flagged_relevant']} of them >= 60")


if __name__ == "__main__":
    main()
