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
from . import tags as _tags

DIVISION_PRIOR = {"8C": 25, "9C": 10, "4A": 5}
KEYWORDS = {
    r"\bsuva\b": 25, r"\buvg\b": 15, r"\blaa\b": 15, r"unfallversicherung": 15, r"assurance-accidents": 15,
    r"assicurazione contro gli infortuni": 15, r"\bunfall": 8, r"\baccident": 8, r"\binfortun": 8,
    r"berufskrankheit|maladie professionnelle|malattia professionale": 10,
    r"integritätsentschädigung|indemnité pour atteinte à l'intégrité": 10,
    r"kausalzusammenhang|lien de causalité|nesso causale": 6, r"\batsg\b|\blpga\b": 5,
    r"invalidenrente|rente d'invalidité": 4, r"taggeld|indemnités journalières": 4,
}


# Subject areas of every ruling Suva summarised (82/82 reference rulings; 0 of 445 rulings outside these
# areas were picked in Oct 2025 - Mar 2026). Matched on the subject line ("Gegenstand" / "Objet" / "Oggetto").
SUBJECT_AREAS = {
    "accident": r"unfallversicherung|assurance[- ]accidents|assicurazione (contro gli )?infortuni|\bUVG\b|\bLAA\b",
    "invalidity": r"invalidenversicherung|assurance[- ]invalidit|assicurazione (per l')?invalidit|\bIVG\b|\bLAI\b",
    "daily_allowance": r"taggeldversicherung|indemnités? journalières?|indennità giornalier",
}
# Appeal decided without going into the merits. Suva picked 3 of 26 such accident rulings (vs 40 of 66 on the merits).
PROCEDURAL = re.compile(r"Prozessvoraussetzung|recevabilit|retrait du recours|Rückzug|Nichteintreten|irrecevab|"
                        r"Revision|unentgeltlich|assistance judiciaire|Rechtsverzögerung|ritardata giustizia", re.I)
_SUBJECT = re.compile(r"\b(Gegenstand|Objet|Oggetto)\s+(.{0,250}?)(Beschwerde gegen|recours contre|ricorso contro|$)")


def classify(j):
    """Subject line, Suva subject areas and procedural flag. Fills j["subject"] if the loader left it empty."""
    subject = j.get("subject") or ""
    if not subject:
        m = _SUBJECT.search(re.sub(r"\s+", " ", (j.get("text") or "")[:6000]))
        subject = m.group(2).strip(" ,;") if m else ""
        j["subject"] = subject
    areas = [a for a, p in SUBJECT_AREAS.items() if re.search(p, subject, re.I)]
    return {"areas": areas, "procedural": bool(PROCEDURAL.search(subject))}


def prefilter(j):
    """Return (score 0-100, matched terms). Rulings outside Suva's subject areas score < PREFILTER_MIN
    and never reach the LLM; everything inside does (keeps 100 % recall on Suva's reference set)."""
    c = classify(j)
    text = ((j.get("subject") or "") + "\n" + (j.get("text") or "")[:20000]).lower()
    score = DIVISION_PRIOR.get(j.get("division") or "", 0)
    hits = []
    for pat, w in KEYWORDS.items():
        if re.search(pat, text):
            score += w
            hits.append(pat.strip("\\b").split("|")[0])
    if not c["areas"]:
        return min(score, 15), hits          # below pipeline.PREFILTER_MIN (20): no LLM call
    return max(20, min(score, 100)), hits


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

Erfahrungswerte aus der bisherigen Auswahl der Suva (Okt. 2025 – März 2026), zur Kalibrierung:
- Unfallversicherung, materiell entschieden: rund 60 % werden zusammengefasst.
- Unfallversicherung, nur prozessual (Nichteintreten, Rückzug, Fristen, unentgeltliche Rechtspflege): rund 12 %,
  nur wenn ein Verfahrensgrundsatz für die Praxis wichtig ist.
- Invalidenversicherung: rund 8 %, nur wenn die Begründung auch für die Unfallversicherung massgebend ist
  (z.B. Invaliditätsbemessung, Einkommensvergleich, Tabellenlöhne/LSE, Beweiswert von Gutachten, Revision).
- Andere Rechtsgebiete: praktisch nie.
Vergib Scores ab 70 nur, wenn das Urteil nach diesen Massstäben zu den zusammengefassten gehört.

Antworte ausschliesslich mit einem JSON-Objekt:
{"score": <int>, "suva_party": <bool>,
 "title_de": "<kurzer Titel auf DEUTSCH, 4-8 Wörter, Kernfrage + Ergebnis, auch wenn das Urteil französisch ist>",
 "title_fr": "<titre court en FRANÇAIS, 4-8 mots, question + issue, même si l'arrêt est en allemand>",
 "explanation_de": "<1-2 Sätze, höchstens 40 Wörter, DEUTSCH: was das Urteil für die Fallbearbeitung der Suva bedeutet (welcher Grundsatz gilt, worauf künftig zu achten ist); kein Sachverhalt, keine Erwägungsnummern; bei geringer Relevanz kurz warum nicht>",
 "explanation_fr": "<1-2 phrases, 40 mots au plus, FRANÇAIS: ce que l'arrêt signifie pour la pratique de la Suva (principe applicable, point d'attention); pas de faits, pas de numéros de considérants>",
 "tags": ["<2-5 Schlagworte, NUR aus der Liste unten, exakt so geschrieben>"]}

Schlagworte (nur Rechtsfragen, kein Ergebnis wie "abgewiesen"; UVG bzw. IV für das Rechtsgebiet):
""" + _tags.prompt_list() + "\n\n" + _tags.LANGUAGE_RULES


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
    c = classify(j)
    kind = "nur prozessual" if c["procedural"] else "materiell"
    user = (f"Urteil {j['docket']} vom {j.get('decision_date') or '?'}"
            f" (Abteilung {j.get('division') or '?'}; Rechtsgebiet: {j.get('subject') or '?'};"
            f" Bereich: {', '.join(c['areas']) or 'keiner'}; Entscheid: {kind})\n\n"
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
    wrong = [k for k in ("title_de", "title_fr", "explanation_de", "explanation_fr")
             if a.get(k) and not _tags.lang_ok(str(a[k]), k[-2:])]
    if wrong:  # e.g. an Italian ruling answered in Italian: one repair call for those fields
        fix = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user},
                        {"role": "assistant", "content": out},
                        {"role": "user", "content": "Diese Felder sind in der falschen Sprache: " + ", ".join(wrong)
                         + ". _de muss Deutsch sein, _fr Französisch. Gib das ganze JSON-Objekt korrigiert aus."}],
                       temperature=0.0, max_tokens=700, json_mode=True)
        try:
            b = llm.parse_json(fix)
            for k in wrong:
                if b.get(k) and _tags.lang_ok(str(b[k]), k[-2:]):
                    a[k] = b[k]
        except ValueError:
            pass
    a["score"] = max(0, min(100, int(a.get("score", 0))))
    a["tags"] = _tags.normalize(a.get("tags") or [])[:6]   # keep only keywords from the fixed list
    fr = [str(t)[:40] for t in (a.get("tags_fr") or [])][:6]
    a["tags_fr"] = fr if len(fr) == len(a["tags"]) else []   # only keep a 1:1 translation (UI pairs them by position)
    return a


def topic_hint(examples, n=40):
    """Short list of topics Suva summarised before, to calibrate the model."""
    lines = []
    for ex in examples[:n]:
        first = re.split(r"(?<=[.!?])\s", ex["de"].strip())[0]
        lines.append(f"- {ex['docket']}: {first[:180]}")
    return "Beispiele für Urteile, welche die Suva zuletzt zusammengefasst hat (Kalibrierung):\n" + "\n".join(lines)
