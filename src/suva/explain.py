"""Specific relevance explanations ("Begründung") for the triage cards, DE + FR.

The first triage prompt produced generic openers ("Das Urteil betrifft …", "Das Bundesgericht hat …").
This pass rewrites the explanation from the ruling itself: lead with the concrete legal question and the
principle the court applied, cite the deciding consideration, then say why it matters (or not) for Suva.
The score is not changed.
"""
import json
import re

from . import config, erwaegungen, llm, postcheck
from .triage import _excerpt

BANNED = re.compile(r"^\s*(Das Bundesgericht|Das BGer|Das Urteil|Dieses Urteil|Im vorliegenden|In diesem Urteil|"
                    r"Le Tribunal fédéral|Le TF|L'arrêt|Cet arrêt|Dans cet arrêt|Dans le présent)", re.I)

SYSTEM = """Du schreibst für den Rechtsdienst der Suva die Kurzbegründung zu einem Urteil des Bundesgerichts:
warum es für die Suva relevant ist oder nicht. Juristinnen und Juristen überfliegen Dutzende solcher Begründungen,
deshalb muss jede sofort zeigen, worum es konkret geht.

Regeln:
- Beginne mit der konkreten Rechtsfrage DIESES Urteils als Stichwort und Doppelpunkt, nach dem Muster
  "<Rechtsfrage> (<Norm>): …". Die Rechtsfrage muss aus dem Urteil stammen, nicht aus einem Beispiel.
  NIE mit "Das Bundesgericht", "Das Urteil", "Dieses Urteil", "Le Tribunal fédéral", "L'arrêt" beginnen.
- Satz 1: was das Gericht entschieden hat und warum, mit der tragenden Erwägung in Klammern, z.B. "(E. 4.4)".
  Nur Nummern aus der Liste der Erwägungen.
- Satz 2: Bedeutung für die Suva (Grundsatz für die Fallbearbeitung, Bestätigung der Praxis, oder warum nur Einzelfall).
- Höchstens 2 Sätze und höchstens 40 Wörter pro Sprache, konkret. Keine Floskeln wie "Für die Suva bedeutet dies",
  keine Daten, Beträge oder Namen. Ergebnis gemäss Dispositiv; wer gewonnen hat (Suva/Versicherer oder versicherte
  Person) muss stimmen. Nennt das Rechtsgebiet die IV, AHV, BVG oder Krankenversicherung, ist KEIN Unfallversicherer
  Partei: die Bedeutung für die Suva dann als Übertragung des Rechtssatzes formulieren.
- Mindestens ein Verweis auf eine Erwägung pro Sprache: "(E. 4.4)" deutsch, "(consid. 4.4)" französisch.
- Französisch: eigenständig formuliert, Fachbegriffe wie in den ATF (consid., assurance-accidents, LAA, LPGA).

Antworte genau in diesem Format, ohne weiteren Text:
DE: <deutsche Begründung, höchstens 2 Sätze>
FR: <französische Begründung, höchstens 2 phrases>"""


def _split(out):
    """'DE: … FR: …' -> {explanation_de, explanation_fr}; tolerant of line breaks inside the text."""
    m = re.search(r"(?:^|\n)\s*\**DE\**\s*:\s*(.+?)\n\s*\**FR\**\s*:\s*(.+)$", out.strip(), re.S)
    if not m:
        return None
    clean = lambda x: re.sub(r"\s+", " ", x).strip()  # noqa: E731
    return {"explanation_de": clean(m.group(1)), "explanation_fr": clean(m.group(2))}


def explain(j, score):
    text = j.get("text") or ""
    user = (f"Urteil {j['docket']} (Rechtsgebiet: {j.get('subject') or '?'}; Relevanz-Score {score}/100)\n\n"
            f"Erwägungen (Nummer: Anfang):\n{erwaegungen.outline(text, 110)}\n\n"
            f"Dispositiv: {erwaegungen.dispositiv(text, 600)}\n\n"
            f"<judgement>\n{_excerpt(text, min(18000, config.LLM_MAX_INPUT_CHARS))}\n</judgement>")
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]

    def ask(m):
        for _ in range(2):  # one retry if the DE/FR blocks can't be found
            out = llm.chat(m, temperature=0.1, max_tokens=600)
            got = _split(out)
            if got:
                return got, out
        raise ValueError("no DE/FR blocks after retry")

    a, raw = ask(msgs)
    if any(BANNED.search(a.get(k) or "") for k in ("explanation_de", "explanation_fr")):
        try:
            a, _ = ask(msgs + [{"role": "assistant", "content": raw},
                               {"role": "user", "content": "Beginne beide Texte mit der konkreten Rechtsfrage dieses Urteils "
                                                           "als Stichwort und Doppelpunkt, nicht mit dem Gericht. Gleiches Format DE:/FR:."}])
        except ValueError:
            pass  # keep the first answer rather than losing the ruling
    issues = postcheck.reason_problems(a.get("explanation_de"), a.get("explanation_fr"), j)
    if issues:
        try:
            a, _ = ask(msgs + [{"role": "assistant", "content": raw},
                               {"role": "user", "content": "Korrigiere: " + "; ".join(issues) + ". Gleiches Format DE:/FR:."}])
        except ValueError:
            pass
    valid = erwaegungen.numbers(text)
    for k in ("explanation_de", "explanation_fr"):
        _, bad = erwaegungen.check_refs(a.get(k) or "", valid)
        for nr in set(bad):
            a[k] = re.sub(r"\s*\((?:E\.|Erw\.|consid\.)\s*" + re.escape(nr) + r"\)", "", a[k])
    return {"de": postcheck.clean_reason(a.get("explanation_de") or ""),
            "fr": postcheck.clean_reason(a.get("explanation_fr") or "")}
