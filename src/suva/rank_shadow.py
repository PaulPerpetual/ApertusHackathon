"""Shadow ranking (experiment): an alternative pass 5, written to rankings_shadow; the live list is untouched.

Lessons from comparing the production ranking with the weighted consensus of independent agents (Gem, Codex, Muse)
on Apr-Jun 2026 (top-10 overlap only 3/10): Apertus over-ranked IV rulings and remands without a new legal rule, and
under-ranked accident-insurance rulings that clarify a rule with broad effect (coverage, deduction practice, causality
standards). Only these general lessons enter the prompt; no case numbers, no agent output.

Instead of one 0-100 judgement, Apertus gives sub-scores; a fixed formula combines them (transparent, fewer ties).
"""
import re

from . import config, erwaegungen, llm
from .triage import _excerpt

SYSTEM = """Du leitest den Rechtsdienst der Suva (Unfallversicherer) und legst fest, in welcher Reihenfolge deine
Juristinnen neue Urteile des Bundesgerichts lesen. Bewerte das Urteil nach diesen Kriterien, jedes einzeln:

K1 Unfallversicherungsrecht materiell (0-5): Geht es um UVG/UVV in der Sache (Unfallbegriff, Kausalität,
   Versicherungsdeckung, Leistungen, Rente, Integritätsentschädigung, Taggeld, Rückfall, Kürzung)? 0 = gar nicht.
K2 Rechtssatz (0-5): Klärt, präzisiert oder ändert das Bundesgericht eine Regel, die über den Fall hinaus gilt?
   5 = neue oder präzisierte Regel, 2 = bekannte Regel ausdrücklich in Erinnerung gerufen, 0 = nur Anwendung auf Tatsachen.
K3 Breitenwirkung (0-5): Wie viele Suva-Fälle betrifft die Regel? (Kausalität bei Vorzustand, Einkommensvergleich,
   Abzüge, Deckungsfragen = viele; seltene Konstellation = wenige.)
K4 Leistungsberechnung oder Deckung beim Unfallversicherer (0-3): Ändert das Urteil, wie ein Unfallversicherer
   Leistungen berechnet oder wer versichert ist?
K5 Verfahrensfalle mit Bedeutung für Unfallversicherer (0-3): Fristen, Anfechtungsobjekt, Legitimation, Zustellung.
A  Abzug (0-5): reine Beweiswürdigung im Einzelfall, reine IV-Spezialfrage, Rückweisung zur Abklärung ohne neuen
   Rechtssatz, Kostenfrage. 0 = trifft nicht zu.

Antworte genau so, jede Zeile mit einer Zahl:
K1: <0-5>
K2: <0-5>
K3: <0-5>
K4: <0-3>
K5: <0-3>
A: <0-5>
GRUND: <ein Satz: welcher Rechtssatz, für wen wichtig>"""

WEIGHTS = {"K1": 4, "K2": 6, "K3": 4, "K4": 3, "K5": 2, "A": -4}
MAX = 4 * 5 + 6 * 5 + 4 * 5 + 3 * 3 + 2 * 3  # 85


def combine(k):
    raw = sum(WEIGHTS[n] * k.get(n, 0) for n in WEIGHTS)
    return max(0.0, min(100.0, round(100 * raw / MAX, 1)))


def assess(j, explanation=""):
    text = j.get("text") or ""
    user = (f"Urteil {j['docket']} (Rechtsgebiet: {j.get('subject') or '?'})\nKurzbeurteilung: {explanation[:500]}\n\n"
            f"Erwägungen (Nummer: Anfang):\n{erwaegungen.outline(text, 90)}\n\nDispositiv: {erwaegungen.dispositiv(text, 400)}\n\n"
            f"<judgement>\n{_excerpt(text, min(14000, config.LLM_MAX_INPUT_CHARS))}\n</judgement>")
    for _ in range(2):
        out = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], temperature=0.0, max_tokens=200)
        k = {}
        for n in WEIGHTS:
            m = re.findall(rf"^\s*\**{n}\**\s*[:=]\s*\**\s*(\d)", out, re.M)
            if m:
                k[n] = min(int(m[-1]), 5 if n in ("K1", "K2", "K3", "A") else 3)
        if len(k) >= 5:
            g = re.findall(r"GRUND\s*:\s*(.+)", out)
            return {"importance": combine(k), "criteria": k, "reason": (g[-1].strip() if g else "")[:300]}
    raise ValueError("criteria missing in answer")


LIST_SYSTEM = """Du leitest den Rechtsdienst der Suva. Ordne die folgenden Urteile nach ihrer Wichtigkeit für die tägliche
Praxis deiner Juristinnen. Zuerst: Urteile, die einen Rechtssatz im Unfallversicherungsrecht klären oder präzisieren und
viele Fälle betreffen (Deckung, Kausalität, Leistungsberechnung). Später: Anwendung bekannter Regeln auf Einzelfälle,
IV-Spezialfragen, Rückweisungen ohne neuen Rechtssatz.
Antworte nur mit der Reihenfolge der Nummern, durch Kommas getrennt."""


def order_top(rows):
    """Listwise ordering of the top rulings: rows have docket, title, reason, summary. Returns indices (0-based)."""
    listing = "\n\n".join(f"[{i + 1}] {r['docket']}: {r.get('title') or ''}\nKern: {(r.get('reason') or '')[:300]}\n"
                          f"Zusammenfassung: {(r.get('summary') or '')[:600]}" for i, r in enumerate(rows))
    for _ in range(2):
        out = llm.chat([{"role": "system", "content": LIST_SYSTEM}, {"role": "user", "content": listing}], temperature=0.0, max_tokens=100)
        nums = list(dict.fromkeys(int(x) for x in re.findall(r"\d+", out) if 1 <= int(x) <= len(rows)))
        if len(nums) >= len(rows) - 2:
            return [n - 1 for n in nums] + [i for i in range(len(rows)) if i + 1 not in nums]
    return list(range(len(rows)))
