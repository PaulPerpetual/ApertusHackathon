"""Summary prompt v2 (experiment): Suva style measured on 54 expert summaries + Codex's accuracy review.

Differences to summarize.py (PR #16):
- Input: Sachverhalt head + ALL considerations + Dispositiv (no silent truncation of the end of the reasoning);
  if the ruling is too long, the middle of the reasoning is shortened and the model is told so.
- Step 1 extracts PROPOSITIONS (question, answer, conditions/exceptions, status fulfilled/rejected/left open,
  consideration, relevance for Suva), separating parties' arguments, medical assessments, lower court and Federal Court.
- Step 2 writes in Suva's measured style: rule first in the present tense (Leitsatz), 1-2 generic sentences of facts,
  fewer/longer sentences, court named at most once, DE 120-240 / FR 150-290 words, 1-2 "(E. x)" references,
  outcome only when it matters and never contradicting the Dispositiv.
- Accuracy rules (from the review): no generalising individual medical findings; remand != final decision;
  keep conditions, exceptions and open questions; transferability judged by the legal rule, not the insurance branch.
Docs: docs/PROMPT_ANALYSIS.md.
"""
import re

import os

from . import config, erwaegungen, llm, postcheck
from .summarize import GLOSSARY, PLACEHOLDER, SUVA_ALIAS, pick_examples

MAX_INPUT = 40000

_DE_FOR_FR = {"LAA": "UVG", "LAINF": "UVG", "OLAA": "UVV", "LPGA": "ATSG", "LAI": "IVG", "RAI": "IVV", "OAI": "IVV",
              "ESS": "LSE", "LTF": "BGG"}
_FR_FOR_DE = {"UVG": "LAA", "UVV": "OLAA", "ATSG": "LPGA", "IVG": "LAI", "IVV": "RAI", "LSE": "ESS", "BGG": "LTF"}


def acronyms(out, lang):
    """Statute abbreviations in the language of the text (Gem: 'LAA/LPGA in German summaries')."""
    table = _DE_FOR_FR if lang == "de" else _FR_FOR_DE
    return re.sub(r"\b(" + "|".join(table) + r")\b", lambda m: table[m.group(1)], out)

EXTRACT_SYSTEM = """Du bist Jurist:in im Rechtsdienst der Suva. Lies das Urteil vollständig und halte die Rechtssätze fest,
bevor irgendein Text formuliert wird. Antworte auf Deutsch, stichwortartig, in genau diesem Aufbau:

SACHVERHALT: 1-2 Zeilen, ohne Namen, Daten, Orte.
ERGEBNIS: was das Dispositiv sagt (gutgeheissen / teilweise gutgeheissen / abgewiesen / Nichteintreten / Rückweisung
  zur Abklärung). Eine Rückweisung zur Abklärung ist weder eine endgültige Ablehnung noch eine Zusprache.
RECHTSSÄTZE: ALLE selbständig relevanten Rechtsfragen, auch Nebenfragen zu Verfahren, Beweis, Legitimation,
  Observation, Beratungspflicht, Revision. Je Rechtsfrage eine Zeile:
  - Frage | Antwort des Bundesgerichts | Voraussetzungen/Ausnahmen | Status (bejaht / verneint / offengelassen /
    angenommen ohne Entscheid) | E. <Nummer> | gilt auch für die Unfallversicherung? (ja/nein, welcher Rechtssatz)
QUELLEN: Unterscheide, was Parteivorbringen, medizinische Einschätzung, Feststellung der Vorinstanz und Würdigung des
  Bundesgerichts ist. Nur die Würdigung des Bundesgerichts ist ein Rechtssatz.
FOKUS: der Rechtssatz, dem das Bundesgericht den grössten Teil seiner Begründung widmet und der für die Suva gilt
  (einer, höchstens zwei). Nicht eine Nebenbemerkung wählen.
ABDECKUNG: "vollständig" oder "unvollständig: <was fehlt>", falls der Text gekürzt ist.
Erfinde nichts. Verallgemeinere keine individuelle Heilungsdauer, Prognose oder Beweiswürdigung zu einer Regel."""

STYLE = {
    "de": """Stil der Suva-Zusammenfassungen (gemessen an 54 echten Zusammenfassungen):
- Beginne mit dem Rechtssatz aus FOKUS als zitierfähigem Satz im PRÄSENS, unpersönlich, oder mit dem, was die Suva
  bzw. der Versicherer getan hat und wie das Bundesgericht das beurteilt. Abwechslungsreich, nicht schematisch mit "Wenn"
  (z.B. "<Begriff> setzt voraus, dass …", "Ein Unfallversicherer darf …, wenn …", "Für <Frage> ist massgebend, …").
  Der Inhalt stammt NUR aus den Rechtssätzen dieses Urteils, und es ist die konkret ENTSCHIEDENE Frage, nicht
  allgemeines Grundlagenwissen.
  Nicht mit "Das Bundesgericht" oder "In diesem Urteil" beginnen.
- Danach 1-2 Sätze Sachverhalt, allgemein ("Ein Versicherter, Maurer, …" bzw. "Eine Versicherte, …", Geschlecht wie
  im Urteil), ohne Daten, Orte und Namen; vom Leiden nur, worauf es rechtlich ankommt. Statt des Rechtsbegehrens
  das Kernargument der beschwerdeführenden Partei, auf das das Bundesgericht antwortet.
- Dann die tragende Begründung; Voraussetzungen, Ausnahmen und offengelassene Fragen bewahren.
- Länge (S2.2): in der Regel 180-240 Wörter, 2-3 Absätze, eher lange Sätze, Fliesstext. Nur wenn das Urteil eine
  einzige prozessuale Frage betrifft: 40-100 Wörter. JEDEN Rechtssatz aus RECHTSSÄTZE aufnehmen, der für die Suva gilt
  (auch Nebenfragen zu Verfahren und Beweis), mit seinen Voraussetzungen; lieber vollständig als knapp.
- Keine Gerichtskosten, Parteientschädigungen, Geburtsjahre, Unfalldaten oder Aktenzeichen der Vorinstanz.
  Nie E. 1 (Eintreten) oder die Kostenfolgen zitieren.
- Das Bundesgericht höchstens einmal nennen. 1-2 Verweise "(E. 5.2)" beim zentralen Rechtssatz.
- Ergebnis nur, wenn es für die Praxis zählt, in einem Satz, genau wie im Dispositiv.
- Immer "die Suva" (nie CNA, SUVA, INSAI), aber NUR wenn die Suva tatsächlich Partei ist; andere Versicherer
  neutral wie Suva selbst: "ein Unfallversicherer"/"der Unfallversicherer", nie Firmennamen (Vaudoise, AXA …);
  IV-Stelle, Krankenkasse usw. mit der Funktion bezeichnen. Keine Platzhalter wie
  "A.________", keine Lücken wie "in ansässige Gesellschaft": neutral umschreiben ("eine Reinigungsfirma").
- Schweizer Fachsprache: UVG, UVV, ATSG, IVG, IVV, LSE (nie LAA, LPGA, OLAA, LAI, RAI, ESS im deutschen Text);
  relatives Wagnis, Listenverletzung, Distorsion/Kontusion, Untersuchungshaft, Valideneinkommen, Einspracheentscheid.""",
    "fr": """Style des résumés de la Suva (mesuré sur 54 résumés réels):
- Commencer par la règle du FOCUS en une phrase citable, au PRÉSENT, impersonnelle, ou par ce que la Suva / l'assureur
  a fait et comment le Tribunal fédéral l'apprécie. Varier, pas systématiquement "Lorsque"
  (p.ex. "<Notion> suppose que …", "Un assureur-accidents peut …, si …", "Est déterminant pour …").
  Le contenu provient UNIQUEMENT des règles de cet arrêt et porte sur la question effectivement TRANCHÉE.
  Ne pas commencer par "Le Tribunal fédéral" ni "Dans cet arrêt".
- Puis 1-2 phrases de faits, générales ("Un assuré, maçon, …" ou "Une assurée, …", selon l'arrêt), sans dates,
  lieux ni noms; de l'atteinte, seulement ce qui compte juridiquement. Au lieu des conclusions, l'argument central
  de la partie recourante auquel le Tribunal fédéral répond.
- Ensuite le raisonnement déterminant; conserver conditions, exceptions et questions laissées ouvertes.
- Longueur (S2.2): en règle générale 220-290 mots, 2-3 paragraphes, phrases plutôt longues, texte suivi. Seulement pour
  une unique question procédurale: 50-120 mots. Reprendre CHAQUE règle pertinente pour la Suva (y compris questions
  annexes de procédure et de preuve) avec ses conditions; plutôt complet que bref.
- Pas de frais judiciaires, dépens, années de naissance, dates d'accident ni références de l'instance précédente.
  Ne jamais citer le consid. 1 (recevabilité) ni les frais.
- Nommer le Tribunal fédéral au plus une fois. 1-2 renvois "(consid. 5.2)" sur la règle centrale.
- L'issue seulement si elle compte pour la pratique, en une phrase, exactement comme le dispositif.
- "la Suva" seulement si la Suva est partie; sinon neutre comme la Suva elle-même:
  "un assureur-accidents"/"l'assureur-accidents", jamais de raison sociale (Vaudoise, AXA …); office AI selon sa fonction. Pas de caractères de substitution ni de lacunes laissées par l'anonymisation.
- Terminologie suisse: LAA, OLAA, LPGA, LAI, RAI, ESS (jamais UVG, ATSG … dans le texte français); entreprise
  téméraire relative, lésion assimilée à un accident, distorsion/contusion, revenu sans invalidité.
- Rédiger directement en français juridique suisse (terminologie des ATF), pas une traduction de l'allemand.""",
}


def full_input(text, limit=MAX_INPUT):
    """Head (parties, Sachverhalt) + ALL considerations + Dispositiv. Only the middle of the reasoning is
    shortened if needed, and the model is told."""
    m = erwaegungen.START.search(text)
    e = erwaegungen.END.search(text)
    head = text[:m.start()] if m else text[:4000]
    body = text[m.start():e.start()] if m and e else text[len(head):]
    disp = text[e.start():] if e else ""
    head = head[:4000]
    room = limit - len(head) - len(disp[:3000])
    note = ""
    if len(body) > room:
        keep_end = room // 2
        body = body[:room - keep_end] + "\n[… Mitte der Erwägungen gekürzt …]\n" + body[-keep_end:]
        note = "HINWEIS: Die Mitte der Erwägungen ist gekürzt; Anfang, Ende und Dispositiv sind vollständig.\n"
    return note + head + "\n" + body + "\n" + disp[:3000]


def extract(j):
    return llm.chat([{"role": "system", "content": EXTRACT_SYSTEM},
                     {"role": "user", "content": f"Urteil {j['docket']}\n<judgement>\n{full_input(j.get('text') or '')}\n</judgement>"}],
                    temperature=0.1, max_tokens=1500)


VERIFY_SYSTEM = """Du bist Gerichtsschreiber:in am Bundesgericht und prüfst eine Urteilszusammenfassung streng gegen das Urteil.
Melde NUR echte Fehler:
(a) Ergebnis widerspricht dem Dispositiv (wer hat gewonnen, Rückweisung vs. endgültiger Entscheid);
(b) falsche Partei oder Versicherung (z.B. Unfallversicherer statt IV-Stelle; Suva als Beschwerdeführerin vs. -gegnerin);
(c) Aussage, die im Urteil nicht steht oder aus einem anderen Urteil stammt;
(d) Rechtssatz falsch zugeordnet (z.B. falsches Adäquanzkriterium, falsche Norm);
(e) offengelassene Frage als entschieden dargestellt, oder Einzelfallwürdigung als allgemeine Regel;
(f) die im Urteil hauptsächlich entschiedene Frage fehlt.
Keine Stilfragen. Antworte nur mit JSON: {"fehler": ["<betroffene Stelle> -> <richtig laut Urteil, mit E.>", ...]}
Leere Liste, wenn die Zusammenfassung korrekt ist."""


def verify(j, notes, out):
    """Faithfulness pass: list of concrete errors in the summary (empty if none or if the check fails)."""
    text = j.get("text") or ""
    user = (f"Urteil {j['docket']} (Rechtsgebiet: {j.get('subject') or '?'})\n"
            f"Dispositiv (verbindlich): {erwaegungen.dispositiv(text, 700)}\n\n"
            f"Rechtssätze laut Auszug:\n{notes}\n\n<judgement>\n{full_input(text, 30000)}\n</judgement>\n\n"
            f"Zu prüfende Zusammenfassung:\n<summary>\n{out}\n</summary>")
    try:
        got = llm.parse_json(llm.chat([{"role": "system", "content": VERIFY_SYSTEM}, {"role": "user", "content": user}],
                                      temperature=0.0, max_tokens=500, json_mode=True))
        return [str(x) for x in (got.get("fehler") or []) if str(x).strip()][:5]
    except Exception:  # noqa: BLE001 - a failed check must not lose the summary
        return []


def write(j, notes, examples, lang, ref=None, long=False):
    text = j.get("text") or ""
    shots = pick_examples(text + notes, examples, lang)
    shot_txt = "\n\n".join(f"Beispiel {i + 1}:\n{ex[lang]}" for i, ex in enumerate(shots))
    target = "Deutsch" if lang == "de" else "Französisch (français)"
    valid = erwaegungen.numbers(text)
    system = f"Du verfasst für den Rechtsdienst der Suva Urteilszusammenfassungen auf {target}.\n\n{STYLE[lang]}\n\n{GLOSSARY}"
    user = (f"Echte Suva-Zusammenfassungen als Stilvorbild:\n\n{shot_txt}\n\n---\n"
            f"Rechtssätze und Fokus zum Urteil {j['docket']}:\n{notes}\n\n"
            f"Dispositiv (verbindlich): {erwaegungen.dispositiv(text, 700)}\n"
            f"Gültige Erwägungsnummern: {', '.join(valid)}\n\n"
            + (f"Bereits geprüfte Fassung in der anderen Sprache (inhaltlich verbindlich: gleiche Rechtssätze, gleiches "
               f"Ergebnis, gleiche Parteien, gleiches Geschlecht; nicht wörtlich übersetzen, sondern in der Fachsprache "
               f"der Zielsprache formulieren):\n{ref}\n\n" if ref else "") +
            f"Schreibe jetzt die Zusammenfassung auf {target}. Nur Rechtssätze aus der Würdigung des Bundesgerichts als "
            f"Regel darstellen; keine individuelle medizinische Feststellung verallgemeinern. Gib nur den Text aus.")
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    out = llm.chat(msgs, temperature=0.3, max_tokens=900).strip()
    def check(t):
        """All automatic checks; returns (problems, conflict, bad_refs)."""
        problems = []
        conflict = erwaegungen.outcome_conflict(t, text)
        if conflict:
            problems.append(f"Ergebnis widerspricht dem Dispositiv: \"{conflict}\"")
        _, bad = erwaegungen.check_refs(t, valid)
        if bad:
            problems.append(f"Erwägungen {', '.join(bad)} gibt es nicht (gültig: {', '.join(valid)})")
        if PLACEHOLDER.search(t):
            problems.append("Platzhalter wie \"A.________\" entfernen")
        if re.match(r"\s*(Das Bundesgericht|In diesem Urteil|Le Tribunal fédéral|Dans cet arrêt)", t):
            problems.append("mit dem Rechtssatz beginnen, nicht mit dem Gericht")
        if re.search(r"\bSuva\b", t) and not re.search(r"\b(Suva|SUVA|CNA|INSAI)\b|Unfallversicherungsanstalt|"
                                                        r"Caisse nationale suisse d'assurance", text):
            problems.append("die Suva ist in diesem Urteil nicht Partei: neutral 'der Unfallversicherer' schreiben")
        if re.search(r"\b(?:in|bei|des|der|vom)\s+(?:ansässige|AG|GmbH|Dr\.)\s+(?:vom|Gesellschaft|in)\b", t):
            problems.append("Lücken der Anonymisierung neutral umschreiben")
        limit = (330 if lang == "de" else 390) if long else (260 if lang == "de" else 310)
        problems += postcheck.problems(postcheck.clean_summary(t, lang), j, lang, words=limit)
        return problems, conflict, bad

    problems, conflict, bad = check(out)

    def fix(t, what):
        return llm.chat(msgs + [{"role": "assistant", "content": t}, {"role": "user", "content": what}],
                        temperature=0.2, max_tokens=900).strip()

    if problems:  # one targeted retry; keep it only if it is really better (Apertus sometimes answers with meta text)
        fixed = fix(out, "Korrigiere: " + "; ".join(problems) + ". Gib den vollständigen korrigierten Text aus, nur den Text.")
        if conflict or bad or postcheck.better(out, fixed, j, lang):
            out = fixed
    if os.getenv("SUMMARY_VERIFY") == "1":  # experimental faithfulness pass (off by default: unstable on Apertus 70B)
        errors = verify(j, notes, out)
        if errors:
            fixed = fix(out, "Eine Prüfung gegen das Urteil ergab diese Fehler:\n- " + "\n- ".join(errors)
                        + "\nKorrigiere nur diese Stellen anhand des Urteils, alles andere unverändert. "
                          "Gleiche Sprache. Gib den vollständigen Text aus.")
            if postcheck.better(out, fixed, j, lang) or not postcheck.problems(fixed, j, lang):
                out = fixed
    # (S2.3 mechanical lengthening for ALL summaries was removed: fewer Suva points and new errors on the dev set.)
    if long:  # top rulings only: deliberate expansion from the extraction, then the SAME checks again
        goal = "220-280 Wörter" if lang == "de" else "260-320 mots"
        longer = fix(out, f"Erweitere die Zusammenfassung auf {goal}: ergänze die Rechtssätze aus RECHTSSÄTZE, die für die "
                          f"Suva gelten und noch fehlen, mit ihren Voraussetzungen, Ausnahmen und offengelassenen Fragen, "
                          f"und erkläre kurz die Bedeutung für die Praxis der Suva. Gleicher Anfang, gleicher Stil, keine "
                          f"neuen Tatsachen, nichts ausserhalb des Urteils. Gib den vollständigen Text aus, nur den Text.")
        p2, c2, b2 = check(longer)
        if p2:
            again = fix(longer, "Korrigiere: " + "; ".join(p2) + ". Gib den vollständigen korrigierten Text aus, nur den Text.")
            if not check(again)[1]:
                longer = again
        # keep the longer text only if it is really longer and introduces no outcome error
        if len(longer.split()) > len(out.split()) * 1.15 and not erwaegungen.outcome_conflict(longer, text):
            out = longer
    out = PLACEHOLDER.sub("", out)
    if re.search(r"\b(Suva|SUVA|CNA|INSAI)\b", text):
        out = SUVA_ALIAS.sub("Suva", out)
    out = acronyms(out, lang)
    out = postcheck.clean_summary(out, lang)
    for nr in set(erwaegungen.check_refs(out, valid)[1]):
        out = re.sub(r"\s*\((?:E\.|Erw\.|consid\.)\s*" + re.escape(nr) + r"\)", "", out)
    return out


def summarize(j, examples, long=False):
    """Write the ruling's own language first (checked against the ruling), then the other language from it,
    so DE and FR state the same rules, outcome, parties and gender."""
    notes = extract(j)
    first = "fr" if (j.get("language") or "") in ("fr", "it") else "de"
    second = "de" if first == "fr" else "fr"
    out = {"notes": notes, first: write(j, notes, examples, first, long=long)}
    cross = os.getenv("SUMMARY_CROSSLANG") == "1"  # experimental: second language written from the first
    out[second] = write(j, notes, examples, second, ref=out[first] if cross else None, long=long)
    return out
