"""Recall rescue ("ATSG pass") for candidates the main triage rejected.

Finding (Apertus vs Codex on the target period): every ruling Codex flagged and Apertus missed was an
IV/procedural ruling that Apertus dismissed with "concerns IV, not UVG", although the deciding rule comes
from the ATSG / BGG / ECHR, which bind the accident insurer exactly like the IV (revision Art. 17 ATSG,
representation Art. 37 ATSG, public hearing Art. 6 ECHR, finality of informal decisions, second expert
opinion). This pass asks Apertus only that question, and requires it to QUOTE the court's sentence that
states the general rule, to avoid the over-calling seen in the v2 'principle pass'.
"""
import re

from . import config, erwaegungen, llm
from .triage import _excerpt

SYSTEM = """Du bist Jurist:in im Rechtsdienst der Suva (Unfallversicherer). Ein Kollege hat dieses Urteil als
"nicht relevant" aussortiert, oft mit der Begründung "betrifft die IV, nicht die UVG". Prüfe, ob er etwas übersehen hat.

Wichtig: Das ATSG (allgemeiner Teil des Sozialversicherungsrechts), das BGG und Art. 6 EMRK / Art. 29 BV gelten für die
Unfallversicherung genau so wie für die Invalidenversicherung. Ein IV-Urteil ist deshalb für die Suva relevant, wenn das
Bundesgericht darin eine solche allgemeine Regel KLÄRT, PRÄZISIERT oder AUSDRÜCKLICH IN ERINNERUNG RUFT, z.B. zu
Revision (Art. 17 ATSG), Wiedererwägung/Rechtskraft (Art. 53 ATSG), Vertretung und Zustellung (Art. 37 ATSG),
Abklärung und Gutachten (Art. 43/44 ATSG, Zweitgutachten), Einsprache/Verfügung (Art. 49/52 ATSG), formlose Erledigung,
öffentliche Verhandlung (Art. 6 EMRK), rechtliches Gehör, Fristen, Parteientschädigung.

NICHT relevant: das Gericht wendet solche Regeln nur auf die Tatsachen des Falls an (Beweiswürdigung, ist dieses
Gutachten überzeugend, wie hoch ist die Arbeitsfähigkeit), oder es geht um IV-Spezialrecht (Eingliederung, IV-Taggeld,
Hilfsmittel, Frühintervention).

Antworte genau in diesem Format:
ENTSCHEID: ja | nein
NORM: <z.B. Art. 17 ATSG, oder leer>
ZITAT: <der Satz aus dem Urteil, in dem das Gericht die allgemeine Regel formuliert, wörtlich, oder leer>
GRUND: <1 Satz>
Antworte "ja" nur, wenn du ein solches wörtliches ZITAT angeben kannst."""


def _field(out, name):
    m = re.findall(rf"^\s*\**{name}\**\s*:\s*(.*)$", out, re.M | re.I)
    return m[-1].strip() if m else ""


def assess(j):
    text = j.get("text") or ""
    user = (f"Urteil {j['docket']} (Rechtsgebiet: {j.get('subject') or '?'})\n"
            f"Erwägungen (Nummer: Anfang):\n{erwaegungen.outline(text, 110)}\n\n"
            f"<judgement>\n{_excerpt(text, config.LLM_MAX_INPUT_CHARS)}\n</judgement>")
    out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                   temperature=0.0, max_tokens=400)
    verdict = _field(out, "ENTSCHEID").lower().startswith("ja")
    quote = _field(out, "ZITAT").strip(' "«»„“')
    # the quote must really be in the ruling (whitespace-insensitive), otherwise the 'yes' doesn't count
    norm_text = re.sub(r"\s+", " ", text)
    quoted_ok = bool(quote) and len(quote) > 25 and re.sub(r"\s+", " ", quote)[:60] in norm_text
    return {"rescue": verdict and quoted_ok, "verdict": verdict, "quote_ok": quoted_ok, "norm": _field(out, "NORM"),
            "quote": quote[:400], "reason": _field(out, "GRUND")}
