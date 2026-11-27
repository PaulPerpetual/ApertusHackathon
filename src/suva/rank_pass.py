"""Pass 5 ("ranking"): fine-grained importance score for rulings already on the hit list.

Why: Suva judges our TOP summaries and our top-30 rulings. The triage scores are coarse (60/65/80/85), so the top of
the list was full of ties: precision@5 on the labelled window was 34 %. This pass gives each hit-list ruling a
fine 0-100 importance score from explicit criteria, used only to ORDER the list (not to select).
"""
import re

from . import config, erwaegungen, llm
from .triage import _excerpt

SYSTEM = """Du leitest den Rechtsdienst der Suva (Unfallversicherer) und entscheidest, welche Urteile des Bundesgerichts
ZUERST zusammengefasst werden. Bewerte die Wichtigkeit für die Praxis der Suva-Juristinnen von 0 bis 100.
Nutze die ganze Skala und vergib keine runden Standardwerte; zwei Urteile sollen selten denselben Wert haben.

Kriterien (je stärker erfüllt, desto höher):
1. Unfallversicherung (UVG/UVV) materiell entschieden: Unfallbegriff, Kausalität, Leistungen, Rente, IE, Taggeld, Rückfall.
2. Klärt, präzisiert oder ändert das Bundesgericht einen Rechtssatz (nicht bloss Anwendung auf Tatsachen)?
3. Die Suva ist Partei, oder ein anderer Unfallversicherer in einer Frage, die die Suva genauso trifft.
4. Breite Wirkung: betrifft viele Fälle (Kausalität bei Vorzustand, Einkommensvergleich, Gutachten, Revision).
5. Fünferbesetzung, Praxisänderung, zur Publikation vorgesehen, oder ausdrücklich "in Erinnerung gerufen".
6. Verfahrensfallen, die Juristinnen kennen müssen (Fristen, Anfechtungsobjekt, Legitimation).
Abzug: reine Beweiswürdigung im Einzelfall, IV-Spezialfragen, Kostenfragen.

Antworte genau so:
WICHTIGKEIT: <0-100>
GRUND: <ein Satz>"""


def assess(j, explanation=""):
    text = j.get("text") or ""
    judges = re.search(r"(Besetzung|Composition|Composizione)(.{0,500}?)(Gerichtsschreiber|Greffi|Cancellier)", text[:6000], re.S)
    panel = ("Besetzung: " + re.sub(r"\s+", " ", judges.group(2))[:250]) if judges else ""
    user = (f"Urteil {j['docket']} (Rechtsgebiet: {j.get('subject') or '?'})\n{panel}\n"
            f"Kurzbeurteilung: {explanation[:500]}\n\nErwägungen (Nummer: Anfang):\n{erwaegungen.outline(text, 90)}\n\n"
            f"Dispositiv: {erwaegungen.dispositiv(text, 400)}\n\n<judgement>\n{_excerpt(text, min(12000, config.LLM_MAX_INPUT_CHARS))}\n</judgement>")
    for _ in range(2):
        out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], temperature=0.0, max_tokens=150)
        m = re.findall(r"WICHTIGKEIT\s*:\s*\**\s*(\d{1,3})", out)
        if m:
            g = re.findall(r"GRUND\s*:\s*(.+)", out)
            return {"importance": max(0, min(100, int(m[-1]))), "reason": (g[-1].strip() if g else "")[:300]}
    raise ValueError("no WICHTIGKEIT in answer")
