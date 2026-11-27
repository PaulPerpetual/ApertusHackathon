"""Recall pass: a second, more generous look at subject-area candidates the main triage scored below the cutoff.

Suva scores the hit list with F2 (recall counts 4x), and in the labelled window Apertus v1 misses 16 % of Suva's
picks. Earlier attempts to make the *main* prompt more generous made Apertus say "yes" to everything (v2, v3 on
/compare). This pass instead only touches the borderline and adds four things the main prompt does not have:

1. Leading-case signal read from the text, no LLM: a five-judge panel (the court sits with five for questions of
   principle). 8 of the 10 five-judge rulings in April-June are already on our list; the signal lifts the other two.
   Phrases like "Praxisänderung" or "zur Publikation vorgesehen" were tried and dropped: in the rulings they almost
   always cite *another* judgement.
2. Self-consistency: the same question asked `samples` times at temperature 0.7, the highest score counts.
3. Nearest labelled neighbours: the 3 most similar rulings Suva did and did not summarise (tf-idf on the
   reasoning), shown with their label, so Apertus judges by analogy to Suva's own choices.
4. Types the main triage misses, as illustrations: Suva summaries of invalidity, procedural accident and
   daily-allowance rulings decided before the evaluation window (no label leakage).

Results go to table recall_assessments; the main assessments are not touched.
"""
import math
import re
from collections import Counter

from . import config, llm, triage
from .triage import _excerpt

# ------------------------------------------------------------------ 1. leading-case signals
_BES = re.compile(r"\b(?:Besetzung|Composition|Composizione)\b(.{0,500}?)\b(?:Gerichtsschreiber|Greffi|Cancellier)", re.S)
_TITLES = re.compile(r"(?i)\b(Bundesrichter(?:in(?:nen)?)?|Mmes?|MM|M|les?|la|Juges?|fédéra(?:le|les|ux|l)|Giudic[ei]|"
                     r"federal[ei]|Präsident(?:in)?|Président(?:e)?|President(?:e|essa)|en qualité de juge unique|"
                     r"als Einzelrichter(?:in)?|vice-?présidente?|präsidierendes Mitglied|membre présidant)\b\.?")

def judges(text):
    """Number of judges on the panel (1, 3 or 5), or None if the 'Besetzung' block is not found."""
    m = _BES.search((text or "")[:4000])
    if not m:
        return None
    seg = _TITLES.sub(" ", re.sub(r"\s+", " ", m.group(1)))
    parts = [p.strip(" .") for p in re.split(r",|\bund\b|\bet\b|\be\b", seg)]
    return len([p for p in parts if re.search(r"[A-ZÄÖÜ]", p)])


def leading_signals(text):
    """List of leading-case signals found in a ruling (empty = none)."""
    return ["Fünferbesetzung"] if judges(text) == 5 else []


# ------------------------------------------------------------------ 3. nearest labelled neighbours
def _reasoning(text):
    """The part that carries the legal substance: from 'Erwägungen'/'Considérant' on, else the whole text."""
    m = re.search(r"\b(Erwägungen|Considérant en droit|Considerando in diritto|in Erwägung)\b", text or "")
    return (text or "")[m.start():] if m else (text or "")


def _tokens(s):
    return re.findall(r"[a-zäöüéèàç]{5,}", s.lower())


class Neighbours:
    """tf-idf cosine over labelled reference rulings: [{docket, subject, text, picked, summary}]."""

    def __init__(self, refs):
        self.refs = refs
        docs = [Counter(_tokens(_reasoning(r["text"])[:15000])) for r in refs]
        self.df = Counter(w for d in docs for w in d)
        self.n = len(docs)
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, c):
        v = {w: tf * math.log((self.n + 1) / (self.df.get(w, 0) + 1)) for w, tf in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        return {w: x / norm for w, x in v.items()}

    def nearest(self, j, k=3):
        """k most similar picked and k most similar skipped rulings, never the ruling itself (leave-one-out)."""
        q = self._vec(Counter(_tokens(_reasoning(j.get("text") or "")[:15000])))
        scored = []
        for r, v in zip(self.refs, self.vecs):
            if r["docket"] == j.get("docket"):
                continue
            scored.append((sum(q.get(w, 0) * x for w, x in v.items()), r))
        scored.sort(key=lambda t: -t[0])
        picked = [r for _, r in scored if r["picked"]][:k]
        skipped = [r for _, r in scored if not r["picked"]][:k]
        return picked, skipped


def neighbour_block(picked, skipped):
    def line(r):
        what = (r.get("summary") or "").strip()
        what = " ".join(re.split(r"(?<=[.!?])\s+", what)[:2])[:300] if what else ""
        return f"- {r['docket']} ({r['subject'][:90]})" + (f": {what}" if what else "")
    return ("Ähnlichste Urteile, welche die Suva ZUSAMMENGEFASST hat:\n" + "\n".join(map(line, picked)) +
            "\n\nÄhnlichste Urteile, welche die Suva NICHT zusammengefasst hat:\n" + "\n".join(map(line, skipped)))


# ------------------------------------------------------------------ 4. illustrations of the types we miss
def illustration_block(examples):
    lines = []
    for ex in examples:
        first = " ".join(re.split(r"(?<=[.!?])\s+", ex["de"].strip())[:2])
        lines.append(f"- {ex['docket']}: {first[:300]}")
    return ("Auch solche Urteile fasst die Suva zusammen (IV, Verfahrensfragen, Taggeld), obwohl sie auf den ersten "
            "Blick nicht nach Unfallversicherung aussehen:\n" + "\n".join(lines))


EXTRA = """
Zweite Durchsicht: Dieses Urteil lag in der ersten Bewertung knapp unter der Schwelle. Die Suva wird an der
VOLLSTÄNDIGKEIT ihrer Liste gemessen: ein verpasstes relevantes Urteil wiegt viermal schwerer als ein unnötig
gelistetes. Prüfe darum besonders, ob das Urteil einen Grundsatz klärt oder in Erinnerung ruft, den die Suva in
ihrer Fallbearbeitung anwenden muss (auch IV, ATSG-Verfahren, Taggeld), und orientiere dich an den ähnlichen
Urteilen, welche die Suva zusammengefasst bzw. nicht zusammengefasst hat."""


def assess(j, neighbours=None, illustrations=(), samples=3, temperature=0.7):
    """Return {'scores': [...], 'score': max, 'leading': [...], 'reason_de': str} for one ruling."""
    lead = leading_signals(j.get("text") or "")
    c = triage.classify(j)
    parts = []
    if illustrations:
        parts.append(illustration_block(illustrations))
    if neighbours is not None:
        parts.append(neighbour_block(*neighbours.nearest(j)))
    if lead:
        parts.append("Hinweise auf einen Leitentscheid: " + ", ".join(lead))
    user = ("\n\n".join(parts) + "\n\n---\n" if parts else "") + (
        f"Urteil {j['docket']} vom {j.get('decision_date') or '?'} (Abteilung {j.get('division') or '?'}; "
        f"Rechtsgebiet: {j.get('subject') or '?'}; Bereich: {', '.join(c['areas']) or 'keiner'}; "
        f"Entscheid: {'nur prozessual' if c['procedural'] else 'materiell'})\n\n"
        f"<judgement>\n{_excerpt(j.get('text') or '', config.LLM_MAX_INPUT_CHARS)}\n</judgement>")
    msgs = [{"role": "system", "content": triage.SYSTEM + EXTRA}, {"role": "user", "content": user}]
    scores, reason = [], ""
    for _ in range(max(1, samples)):
        try:
            a = llm.parse_json(llm.chat(msgs, temperature=temperature, max_tokens=700, json_mode=True))
        except (ValueError, llm.LLMError):
            continue
        s = max(0, min(100, int(a.get("score", 0) or 0)))
        if not scores or s > max(scores):
            reason = a.get("explanation_de") or ""
        scores.append(s)
    return {"scores": scores, "score": max(scores) if scores else None, "leading": lead, "reason_de": reason}


def combined(ai_score, recall_score=None, leading=(), lead_floor=70):
    """Score for the hit list: the higher of the main and the recall pass; leading cases at least `lead_floor`."""
    s = max(x for x in (ai_score or 0, recall_score or 0))
    return max(s, lead_floor) if leading else s
