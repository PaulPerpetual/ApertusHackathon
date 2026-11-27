"""Second triage pass for invalidity-insurance (IV/AI) rulings.

Why: in the labelled window (Oct 2025 - Mar 2026) Suva summarised 16 of 197 IV rulings (8 %), and the
general triage prompt scored most of them 0 ("IV, not UVG"). Suva's IV summaries are almost never about
the individual disability case; they keep IV rulings that settle a principle an accident insurer must
also apply (ATSG procedure, expert assessments, evidence, ECHR hearing, revision, helplessness, deadlines,
standing). This pass asks exactly that question and returns a graded score, so the IV cutoff can be tuned
separately for F2.

Illustrations are Suva IV summaries decided BEFORE the evaluation window (no label leakage), passed in by
the caller via `illustrations`.
"""
import re

from . import config, llm
from .triage import _excerpt

SYSTEM = """Du bist Jurist:in im Rechtsdienst der Suva (Unfallversicherer). Du prüfst ein Urteil des Bundesgerichts
aus der INVALIDENVERSICHERUNG (IV). Die Suva fasst nur wenige IV-Urteile zusammen (rund 1 von 10), nämlich solche,
die einen Grundsatz klären oder in Erinnerung rufen, den auch ein Unfallversicherer anwenden muss, z.B.:
- Verfahren nach ATSG und BGG: rechtliches Gehör, öffentliche Verhandlung (Art. 6 EMRK), Fristen, Legitimation,
  Rechtsverzögerung, Aufklärungs- und Beratungspflicht, Vorbescheid/Einsprache.
- Medizinische Abklärung: Ablauf und Beweiswert von Gutachten (MEDAS, polydisziplinär), Rolle der Gutachter,
  Mitwirkung und Glaubwürdigkeit der versicherten Person, Abklärungsberichte vor Ort.
- Allgemeine Leistungsbegriffe, die auch im UVG gelten: Rentenrevision (Art. 17 ATSG, Vergleichszeitpunkte),
  Hilflosigkeit/Hilflosenentschädigung, Verwertbarkeit der Restarbeitsfähigkeit, Arbeitsunfähigkeit (Art. 6 ATSG).
NICHT zusammengefasst wird die Routine: gefestigte Rechtsprechung wird ohne neue Erkenntnis auf einen Einzelfall
angewendet (z.B. übliche Invaliditätsbemessung, Beweiswürdigung im konkreten Fall, reine IV-Spezialfragen wie
berufliche Massnahmen, Frühintervention, Kinderrenten, IV-spezifische Eingliederung).

Antworte ausschliesslich mit JSON:
{"score": <0-100, Wahrscheinlichkeit in %, dass die Suva dieses Urteil zusammenfasst>,
 "principle": "<der übertragbare Grundsatz in einem Satz, oder leer>",
 "reason_de": "<1-2 Sätze Begründung>"}
Die meisten IV-Urteile erhalten 0-20. Gib 40+ nur, wenn ein für die Unfallversicherung massgebender Grundsatz
geklärt oder ausdrücklich in Erinnerung gerufen wird."""


def illustration_block(examples):
    lines = []
    for ex in examples:
        first = " ".join(re.split(r"(?<=[.!?])\s+", ex["de"].strip())[:2])
        lines.append(f"- {ex['docket']}: {first[:350]}")
    return "Beispiele für IV-Urteile, welche die Suva früher zusammengefasst hat:\n" + "\n".join(lines)


def assess_iv(j, illustrations):
    user = (f"{illustration_block(illustrations)}\n\n---\n"
            f"Urteil {j['docket']} vom {j.get('decision_date') or '?'} (Rechtsgebiet: {j.get('subject') or '?'})\n\n"
            f"<judgement>\n{_excerpt(j.get('text') or '', config.LLM_MAX_INPUT_CHARS)}\n</judgement>")
    out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                   temperature=0.0, max_tokens=400, json_mode=True)
    a = llm.parse_json(out)
    a["score"] = max(0, min(100, int(a.get("score", 0))))
    return a
