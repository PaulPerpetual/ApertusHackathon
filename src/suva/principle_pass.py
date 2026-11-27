"""Second triage pass v2 ("principle pass") for invalidity rulings and procedural accident rulings.

Lesson from comparing Apertus with a second model (Codex, development only) on 40 labelled rulings:
the deciding question is "does the court state a general rule, or assess an individual case?".
Apertus over-included routine IV rulings (individual work-capacity assessments) and missed
procedural rulings that recall a general rule (binding force of decisions, Art. 37 ATSG representation,
Art. 6 ECHR hearings). This pass makes Apertus answer that question explicitly, step by step, before
scoring. The scoring itself stays 100 % Apertus.
"""
from . import config, llm
from .triage import _excerpt

SYSTEM = """Du bist Jurist:in im Rechtsdienst der Suva (Schweizerische Unfallversicherungsanstalt, UVG).
Du prüfst ein Urteil des Bundesgerichts. Die Suva fasst ein solches Urteil nur zusammen, wenn das Bundesgericht
darin einen ALLGEMEINEN GRUNDSATZ klärt, präzisiert oder ausdrücklich in Erinnerung ruft, den auch ein
Unfallversicherer in anderen Fällen anwenden muss.

Unterscheide streng:
- GRUNDSATZ: eine Regel, die über den konkreten Fall hinaus gilt. Beispiele: Rechtskraft und Tragweite einer
  Verfügung; Zustellung, Vertretung, Fristen (ATSG, BGG); rechtliches Gehör; Anspruch auf öffentliche Verhandlung
  (Art. 6 EMRK) und wann sie verweigert werden darf; Anforderungen an Gutachten und Zweitgutachten; Beweiswert;
  Revision (Art. 17 ATSG: was ist eine relevante Änderung?); Wiedererwägung; Parteientschädigung bei Rückweisung;
  Begriffe wie Arbeitsunfähigkeit, Hilflosigkeit, Einkommensvergleich, Tabellenlöhne, soweit das Gericht die Regel
  selbst klärt.
- EINZELFALL: das Gericht würdigt Tatsachen und Beweise eines konkreten Falles (ist dieses Gutachten überzeugend,
  wie hoch ist die Arbeitsfähigkeit dieser Person, welche Verweisungstätigkeit ist zumutbar), auch wenn es dabei
  bekannte Grundsätze zitiert. Das ist der häufigste Fall (rund 9 von 10 IV-Urteilen).
- Reine IV-Spezialfragen (berufliche Eingliederung, Frühintervention, IV-spezifische Leistungen) sind für die Suva
  nicht massgebend, auch wenn ein Grundsatz geklärt wird.

Gehe in dieser Reihenfolge vor und antworte ausschliesslich mit JSON:
{"rechtsfrage": "<die streitige Rechtsfrage in einem Satz>",
 "grundsatz": "<der allgemeine Grundsatz, den das Bundesgericht klärt oder in Erinnerung ruft, oder leer>",
 "typ": "grundsatz" | "einzelfall",
 "fuer_uvg_massgebend": true | false,
 "score": <0-100: Wahrscheinlichkeit in %, dass die Suva das Urteil zusammenfasst>,
 "reason_de": "<1-2 Sätze>"}
Richtwerte: grundsatz + fuer_uvg_massgebend → 60-90; grundsatz, aber IV-spezifisch → 15-35; einzelfall → 0-15."""


def assess(j):
    user = (f"Urteil {j['docket']} vom {j.get('decision_date') or '?'} (Rechtsgebiet: {j.get('subject') or '?'})\n\n"
            f"<judgement>\n{_excerpt(j.get('text') or '', config.LLM_MAX_INPUT_CHARS)}\n</judgement>")
    out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                   temperature=0.0, max_tokens=500, json_mode=True)
    a = llm.parse_json(out)
    a["score"] = max(0, min(100, int(a.get("score", 0))))
    return a
