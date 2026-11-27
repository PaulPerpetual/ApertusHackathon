"""Pass 4 ("adjudicator"): a critical review of the first three Apertus passes, sorting each candidate into tiers.

Earlier extra passes (v2 principle, v3 ATSG rescue) each asked ONE isolated question and Apertus said "yes" almost
always. Here Apertus sees the competing evidence side by side (main triage score + reason, IV second pass, ATSG rescue
with its quote and norm) plus the ruling's considerations and Dispositiv, and must weigh it:
  Tier 1 = relevant for Suva, Tier 2 = Grenzfall (plausible, a lawyer should look), Tier 3 = not relevant.
Recall matters more than precision for Suva ("did you find all relevant judgements?"): in doubt, Tier 2.
"""
import re

from . import config, erwaegungen, llm
from .triage import _excerpt

SYSTEM = """Du bist erfahrene:r Jurist:in im Rechtsdienst der Suva (Unfallversicherer) und prüfst die Vorschläge von drei
Assistenten zu einem Urteil des Bundesgerichts KRITISCH. Entscheide, ob die Suva das Urteil intern zusammenfassen würde.

Erfahrungswerte der Suva: von 100 Urteilen in Unfall-, Invaliden- und Taggeldversicherung fasst sie etwa 20 zusammen:
- Unfallversicherung, materiell entschieden: rund 60 %; nur prozessual: selten (rund 1 von 8).
- Invalidenversicherung: rund 1 von 12, nämlich wenn ein Rechtssatz geklärt oder ausdrücklich in Erinnerung gerufen
  wird, den auch ein Unfallversicherer anwenden muss (ATSG-Verfahren, Gutachten/Beweis, Revision Art. 17 ATSG,
  Einkommensvergleich/Tabellenlöhne, Hilflosigkeit, öffentliche Verhandlung, Legitimation, Fristen).
Nicht zusammengefasst: Routine-Anwendung gefestigter Rechtsprechung auf Tatsachen eines Einzelfalls, reine
IV-Spezialfragen (Eingliederung, Assistenzbeitrag, Hilfsmittel), reine Kosten- oder Nichteintretensentscheide ohne
Grundsatz. Ein wörtliches Zitat, das nur bekannte Rechtsprechung wiedergibt, ist noch keine Klärung.

Prüfe die Argumente der Assistenten am Urteil selbst. Ordne dann ein:
TIER 1 = die Suva würde es sehr wahrscheinlich zusammenfassen.
TIER 2 = Grenzfall: ernsthaft möglich, eine Juristin sollte es ansehen.
TIER 3 = nicht relevant für die Suva.
Ein verpasstes relevantes Urteil ist schlimmer als ein Grenzfall zu viel: im Zweifel TIER 2 statt TIER 3.
Aber nicht alles ist ein Grenzfall: Routine und IV-Spezialfragen sind TIER 3.

Antworte genau so:
TIER: 1 | 2 | 3
GRUND: <ein Satz, konkret: welcher Rechtssatz, oder warum nur Routine>"""


def assess(j, evidence):
    text = j.get("text") or ""
    user = (f"Urteil {j['docket']} (Rechtsgebiet: {j.get('subject') or '?'})\n\n"
            f"VORSCHLÄGE DER ASSISTENTEN:\n{evidence}\n\n"
            f"Erwägungen (Nummer: Anfang):\n{erwaegungen.outline(text, 100)}\n\n"
            f"Dispositiv: {erwaegungen.dispositiv(text, 500)}\n\n"
            f"<judgement>\n{_excerpt(text, min(14000, config.LLM_MAX_INPUT_CHARS))}\n</judgement>")
    for _ in range(2):
        out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                       temperature=0.0, max_tokens=200)
        m = re.findall(r"TIER\s*:\s*\**\s*([123])", out)
        if m:
            g = re.findall(r"GRUND\s*:\s*(.+)", out)
            return {"tier": int(m[-1]), "reason": (g[-1].strip() if g else "")[:400]}
    raise ValueError("no TIER in answer")


def evidence_text(r):
    """The first three passes, as the adjudicator sees them."""
    lines = [f"Assistent 1 (Triage): Score {r.get('main')}/100. {(r.get('explanation') or '').strip()[:500]}"]
    if r.get("iv") is not None:
        lines.append(f"Assistent 2 (IV-Prüfung, nur IV-Urteile): {r['iv']} % Wahrscheinlichkeit; Grundsatz: {r.get('iv_principle') or '-'}")
    if r.get("rescue_verdict") is not None:
        verdict = "JA, übertragbarer Rechtssatz" if r["rescue_verdict"] else "nein"
        lines.append(f"Assistent 3 (ATSG-Prüfung): {verdict}; Norm: {r.get('rescue_norm') or '-'}; "
                     f"Zitat: {(r.get('rescue_quote') or '-')[:300]}; Grund: {r.get('rescue_reason') or '-'}")
    else:
        lines.append("Assistent 3 (ATSG-Prüfung): nicht durchgeführt (Assistent 1 war bereits positiv)")
    return "\n".join(lines)
