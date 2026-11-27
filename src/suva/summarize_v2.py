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

from . import config, erwaegungen, llm
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
- Beginne mit dem Rechtssatz aus FOKUS als zitierfähigem Satz im PRÄSENS, unpersönlich (Muster: "Wenn <Voraussetzung>,
  dann <Rechtsfolge>." bzw. "<Begriff> setzt voraus, dass …"). Der Inhalt stammt NUR aus den Rechtssätzen dieses Urteils.
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
- Commencer par la règle du FOCUS en une phrase citable, au PRÉSENT, impersonnelle (modèle: "Lorsque <condition>,
  <conséquence juridique>."). Le contenu provient UNIQUEMENT des règles de cet arrêt.
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


def write(j, notes, examples, lang):
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
            f"Schreibe jetzt die Zusammenfassung auf {target}. Nur Rechtssätze aus der Würdigung des Bundesgerichts als "
            f"Regel darstellen; keine individuelle medizinische Feststellung verallgemeinern. Gib nur den Text aus.")
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    out = llm.chat(msgs, temperature=0.3, max_tokens=900).strip()
    problems = []
    conflict = erwaegungen.outcome_conflict(out, text)
    if conflict:
        problems.append(f"Ergebnis widerspricht dem Dispositiv: \"{conflict}\"")
    _, bad = erwaegungen.check_refs(out, valid)
    if bad:
        problems.append(f"Erwägungen {', '.join(bad)} gibt es nicht (gültig: {', '.join(valid)})")
    if PLACEHOLDER.search(out):
        problems.append("Platzhalter wie \"A.________\" entfernen")
    if re.match(r"\s*(Das Bundesgericht|In diesem Urteil|Le Tribunal fédéral|Dans cet arrêt)", out):
        problems.append("mit dem Rechtssatz beginnen, nicht mit dem Gericht")
    if re.search(r"\bSuva\b", out) and not re.search(r"\b(Suva|SUVA|CNA|INSAI)\b|Unfallversicherungsanstalt|"
                                                      r"Caisse nationale suisse d'assurance", text):
        problems.append("die Suva ist in diesem Urteil nicht Partei: neutral 'der Unfallversicherer' schreiben")
    if re.search(r"\b(?:in|bei|des|der|vom)\s+(?:ansässige|AG|GmbH|Dr\.)\s+(?:vom|Gesellschaft|in)\b", out):
        problems.append("Lücken der Anonymisierung neutral umschreiben")
    if problems:
        out = llm.chat(msgs + [{"role": "assistant", "content": out},
                               {"role": "user", "content": "Korrigiere: " + "; ".join(problems) + ". Nur der Text."}],
                       temperature=0.2, max_tokens=900).strip()
    # (S2.3 mechanical lengthening removed: longer text but fewer Suva points and new errors on the dev set)
    out = PLACEHOLDER.sub("", out)
    if re.search(r"\b(Suva|SUVA|CNA|INSAI)\b", text):
        out = SUVA_ALIAS.sub("Suva", out)
    out = acronyms(out, lang)
    for nr in set(erwaegungen.check_refs(out, valid)[1]):
        out = re.sub(r"\s*\((?:E\.|Erw\.|consid\.)\s*" + re.escape(nr) + r"\)", "", out)
    return out


def summarize(j, examples):
    notes = extract(j)
    return {"notes": notes, "de": write(j, notes, examples, "de"), "fr": write(j, notes, examples, "fr")}
