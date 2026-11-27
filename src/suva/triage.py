"""Relevance triage: cheap rule-based prefilter, then Apertus scores and explains.

Score scale (0-100), from Suva's legal service point of view:
  80-100  must summarise: new or clarified principle in accident insurance (UVG/LAA), or Suva is a party
          and the reasoning matters for case handling
  60-79   relevant: applies settled UVG case law in an instructive way, or a general social-insurance
          procedure point (ATSG/LPGA, evidence, expert reports, EMRK hearings) that Suva meets daily
  30-59   peripheral: other social insurance (IV, BVG, ALV) with only indirect relevance
  0-29    not relevant
"""
import re

from . import llm, config

DIVISION_PRIOR = {"8C": 25, "9C": 10, "4A": 5}
KEYWORDS = {
    r"\bsuva\b": 25, r"\buvg\b": 15, r"\blaa\b": 15, r"unfallversicherung": 15, r"assurance-accidents": 15,
    r"assicurazione contro gli infortuni": 15, r"\bunfall": 8, r"\baccident": 8, r"\binfortun": 8,
    r"berufskrankheit|maladie professionnelle|malattia professionale": 10,
    r"integritätsentschädigung|indemnité pour atteinte à l'intégrité": 10,
    r"kausalzusammenhang|lien de causalité|nesso causale": 6, r"\batsg\b|\blpga\b": 5,
    r"invalidenrente|rente d'invalidité": 4, r"taggeld|indemnités journalières": 4,
}


def prefilter(j):
    """Return (score 0-100, matched terms). Used to skip obviously irrelevant judgements cheaply."""
    text = ((j.get("subject") or "") + "\n" + (j.get("text") or "")[:20000]).lower()
    score = DIVISION_PRIOR.get(j.get("division") or "", 0)
    hits = []
    for pat, w in KEYWORDS.items():
        if re.search(pat, text):
            score += w
            hits.append(pat.strip("\\b").split("|")[0])
    return min(score, 100), hits


SYSTEM = """Du bist juristische:r Mitarbeiter:in im Rechtsdienst der Suva (Schweizerische Unfallversicherungsanstalt).
Du sichtest neu publizierte Urteile des Schweizerischen Bundesgerichts und beurteilst, ob sie für die Suva
relevant sind und intern zusammengefasst werden sollen.

Bewertungsskala (score 0-100):
- 80-100: neuer oder präzisierter Grundsatz im Unfallversicherungsrecht (UVG/LAA), oder die Suva ist Partei
  und die Begründung ist für die Fallbearbeitung wichtig (z.B. Kausalität, Unfallbegriff, Invalideneinkommen,
  Integritätsentschädigung, Rentenrevision, Taggeld, Rückfall, Berufskrankheit, Leistungskürzung).
- 60-79: wendet die Rechtsprechung zum UVG lehrreich an, oder klärt eine allgemeine Verfahrens-/Beweisfrage
  im Sozialversicherungsrecht (ATSG, Gutachten, rechtliches Gehör, öffentliche Verhandlung nach Art. 6 EMRK),
  die für einen Unfallversicherer täglich relevant ist.
- 30-59: andere Sozialversicherung (IV, BVG, ALV, KVG) mit nur indirekter Bedeutung für die Suva.
- 0-29: nicht relevant (z.B. Straf-, Zivil-, Steuerrecht ohne Bezug zur Unfallversicherung,
  reine Nichteintretensentscheide).

Antworte ausschliesslich mit einem JSON-Objekt:
{"score": <int>, "suva_party": <bool>,
 "title_de": "<prägnanter Titel, max. 12 Wörter>", "title_fr": "<titre concis, max. 12 mots>",
 "explanation_de": "<2-3 Sätze: warum (nicht) relevant, welche Rechtsfrage, Ergebnis>",
 "explanation_fr": "<2-3 phrases: pourquoi (pas) pertinent, question juridique, issue>",
 "tags": ["<3-5 kurze deutsche Schlagworte>"]}"""


def _excerpt(text, limit):
    """Keep the head (parties, Sachverhalt) and the start of the Erwägungen; they carry most signal."""
    if len(text) <= limit:
        return text
    m = re.search(r"\n\s*(Erwägungen?|Considérant en droit|Considerando in diritto)\s*:?\s*\n", text)
    head = limit // 3
    if m and m.start() > head:
        return text[:head] + "\n[...]\n" + text[m.start():m.start() + limit - head]
    return text[:limit]


def assess(j, examples_hint=None):
    """Return assessment dict for a judgement dict (needs docket, text or subject)."""
    body = j.get("text") or j.get("subject") or ""
    user = (f"Urteil {j['docket']} vom {j.get('decision_date') or '?'}"
            f" (Abteilung {j.get('division') or '?'}; Rechtsgebiet: {j.get('subject') or '?'})\n\n"
            f"<judgement>\n{_excerpt(body, config.LLM_MAX_INPUT_CHARS)}\n</judgement>")
    if examples_hint:
        user = examples_hint + "\n\n" + user
    out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                   temperature=0.0, max_tokens=700, json_mode=True)
    try:
        a = llm.parse_json(out)
    except ValueError:
        # one repair attempt
        out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user},
                        {"role": "assistant", "content": out},
                        {"role": "user", "content": "Bitte nur das JSON-Objekt, ohne weiteren Text."}],
                       temperature=0.0, max_tokens=700, json_mode=True)
        a = llm.parse_json(out)
    a["score"] = max(0, min(100, int(a.get("score", 0))))
    a["tags"] = [str(t)[:40] for t in (a.get("tags") or [])][:6]
    return a


def topic_hint(examples, n=40):
    """Short list of topics Suva summarised before, to calibrate the model."""
    lines = []
    for ex in examples[:n]:
        first = re.split(r"(?<=[.!?])\s", ex["de"].strip())[0]
        lines.append(f"- {ex['docket']}: {first[:180]}")
    return "Beispiele für Urteile, welche die Suva zuletzt zusammengefasst hat (Kalibrierung):\n" + "\n".join(lines)
