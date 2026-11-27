"""Write Suva-style summaries in German and French.

Each language is written separately from the judgement (not translated), with few-shot examples
in that language picked by similarity to the judgement, plus a DE/FR terminology glossary.
Two-step approach to reduce invented citations: first extract the key considerations with their
numbers, then write the summary only from those notes.
"""
import math
import re
from collections import Counter

from . import llm, config
from .triage import _excerpt
from . import erwaegungen

PLACEHOLDER = re.compile(r"\b[A-Z]{1,2}\._{3,}(?:\s*\([^)]*\))?,?\s*")  # anonymised party, e.g. "A.________"

GLOSSARY = """Terminologie DE ↔ FR (verbindlich):
Bundesgericht (BGer) ↔ Tribunal fédéral (TF) | Erw. ↔ consid. | Urteil ↔ arrêt | Beschwerdeführer/in ↔ recourant/e
Versicherte/r ↔ assuré/e | Unfallversicherung (UVG) ↔ assurance-accidents (LAA) | ATSG ↔ LPGA | IVG ↔ LAI
UVV ↔ OLAA | IVV ↔ RAI | ATSV ↔ OPGA | BVG ↔ LPP (keine italienischen Abkürzungen wie OAI/LAINF in DE oder FR)
Invalidenrente ↔ rente d'invalidité | Invaliditätsgrad ↔ taux d'invalidité | Valideneinkommen ↔ revenu sans invalidité
Invalideneinkommen ↔ revenu d'invalide | Tabellenlohn (LSE) ↔ salaire statistique (ESS) | Leidensabzug ↔ abattement
Integritätsentschädigung ↔ indemnité pour atteinte à l'intégrité | Taggeld ↔ indemnité journalière
natürlicher/adäquater Kausalzusammenhang ↔ lien de causalité naturelle/adéquate | Rückfall ↔ rechute
Spätfolgen ↔ séquelles tardives | Berufskrankheit ↔ maladie professionnelle | Heilbehandlung ↔ traitement médical
Fallabschluss ↔ clôture du cas | Rentenrevision ↔ révision de la rente | Gutachten ↔ expertise
rechtliches Gehör ↔ droit d'être entendu | öffentliche Verhandlung ↔ débats publics | Vorinstanz ↔ autorité précédente
Kantonsgericht/Versicherungsgericht ↔ tribunal cantonal des assurances | gutheissen ↔ admettre | abweisen ↔ rejeter
zurückweisen ↔ renvoyer | Nichteintreten ↔ irrecevabilité
relatives/absolutes Wagnis ↔ entreprise téméraire relative/absolue | Listenverletzung (unfallähnliche Körperschädigung)
↔ lésion assimilée à un accident | Distorsion/Kontusion ↔ distorsion/contusion | Untersuchungshaft ↔ détention provisoire
Einspracheentscheid ↔ décision sur opposition | Status quo sine/ante ↔ statu quo sine/ante | Tabellenlohnabzug ↔ abattement
Fachhochschule (FH) ↔ haute école spécialisée (HES) | IV-Stelle ↔ office AI | kantonales Gericht ↔ tribunal cantonal
Abkürzungen von Behörden, Schulen und Abschlüssen immer in der Zielsprache (DE "Architekt FH", nie "Architekt HES").
Geschlecht der Parteien wie im Urteil: "die Versicherte"/"l'assurée" bei einer Frau, "der Versicherte"/"l'assuré" bei
einem Mann; im Zweifel "die versicherte Person"/"la personne assurée"."""

STYLE = {
    "de": """Stil der Suva-Zusammenfassungen (Deutsch):
- KURZ: 100-170 Wörter, höchstens 3 kurze Absätze, sachlicher Fliesstext, keine Aufzählungen, keine Überschriften.
  Nur das, was eine Juristin der Suva für ihre Praxis wissen muss; keine Prozessgeschichte, keine Daten,
  keine Wiederholungen.
- Einstieg: bevorzugt mit der Rechtsfrage oder dem Grundsatz ("In diesem Urteil prüfte das Bundesgericht, ob ..."
  oder "Erwartet der Versicherer ..., muss er ..."); sonst den Sachverhalt in einem Satz ("Versicherter, Maurer, der ...").
- Kern sind die Grundsätze und die Begründung des Bundesgerichts: die tragenden Argumente als Rechtssätze im
  Präsens ("Die Reinigung von Büros fällt unter Art. 73 lit. b UVV."; "Das BGer bestätigt ..."), der Sachverhalt
  knapp in der Vergangenheit ("Die Suva verglich ...").
- Weglassen: Unfalldaten, Verfahrensgeschichte durch die Instanzen, Gerichtskosten, Daten von Verfügungen.
  Sachverhalt nur so weit, wie er für den Grundsatz nötig ist (z.B. Ausbildung bei der Frage des Kompetenzniveaus).
  Vom Gesundheitsschaden nur das nennen, worauf es rechtlich ankommt (z.B. die Armparese bei der Hilflosigkeit);
  keine Geburtsjahre, Kantone oder Orte.
- Statt des Rechtsbegehrens ("beantragt 30 % oder Rückweisung") das Kernargument der beschwerdeführenden Partei
  nennen, auf das das Bundesgericht antwortet ("machte geltend, es drohe eine schwere Arthrose").
- Ist die Suva Partei, aus ihrer Sicht schreiben: was die Suva entschieden oder geltend gemacht hat und ob das
  BGer ihr folgt.
- Sparsam zitieren: 1-2 Verweise auf die tragende Erwägung im Format "(E. 5.2)", nicht in jedem Satz.
  Nur Nummern aus der Liste "Erwägungen des Urteils" verwenden.
- Bundesgericht als "das Bundesgericht" oder "das BGer". Ergebnis am Schluss in einem Satz
  ("Das Bundesgericht wies die Beschwerde ab." / "hiess die Beschwerde gut").
- Die Suva heisst immer "die Suva" (nie CNA, SUVA oder INSAI). Keine Personennamen und keine Platzhalter wie
  "A.________"; Parteien als "der Versicherte" bzw. "die Versicherte" (Geschlecht wie im Urteil), "die Beschwerdeführerin", "die Suva".""",
    "fr": """Style des résumés de la Suva (français):
- COURT: 100-180 mots, au plus 3 paragraphes courts, texte suivi et factuel, pas d'énumérations ni de titres.
  Seulement ce qu'un juriste de la Suva doit savoir pour sa pratique; pas d'historique de procédure, pas de dates,
  pas de répétitions.
- Début: de préférence par la question juridique ou le principe ("Dans cet arrêt, le Tribunal fédéral a examiné si ..."
  ou "Lorsque l'assureur attend ..., il doit ..."); sinon les faits en une phrase ("Assuré, carreleur, qui ...").
- L'essentiel: les principes et le raisonnement du Tribunal fédéral, énoncés comme règles au présent
  ("Le nettoyage des bureaux tombe sous l'art. 73 let. b OLAA."; "Le TF confirme ..."), les faits brièvement au passé
  ("La Suva a procédé ...").
- Omettre: dates d'accident, historique de la procédure, frais judiciaires, dates des décisions. Les faits
  seulement dans la mesure nécessaire au principe. De l'atteinte à la santé, ne citer que ce qui compte
  juridiquement (p.ex. la parésie du bras pour l'impotence); pas d'année de naissance, de canton ni de lieu.
- Au lieu des conclusions ("conclut à 30 % ou au renvoi"), indiquer l'argument central de la partie recourante
  auquel le Tribunal fédéral répond ("faisait valoir un risque d'arthrose grave").
- Si la Suva est partie, écrire de son point de vue: ce que la Suva a décidé ou fait valoir et si le TF la suit.
- Citer avec parcimonie: 1-2 renvois au considérant déterminant, au format "(consid. 5.2)", pas à chaque phrase.
  N'utiliser que des numéros de la liste "Considérants de l'arrêt".
- "le Tribunal fédéral" ou "le TF". Indiquer l'issue à la fin en une phrase ("Le Tribunal fédéral a rejeté le recours.").
- Toujours "la Suva" (jamais CNA, SUVA ou INSAI). Pas de noms de personnes ni de caractères de substitution comme
  "A.________"; parties: "l'assuré" ou "l'assurée" (selon l'arrêt), "la recourante", "la Suva".
- Rédiger directement en français juridique suisse, ce n'est pas une traduction de l'allemand.""",
}

MAX_WORDS = {"de": 170, "fr": 180}
SUVA_ALIAS = re.compile(r"(?:Caisse nationale suisse d'assurance en cas d'accidents|Schweizerische Unfallversicherungsanstalt|Istituto nazionale svizzero di assicurazione contro gli infortuni)(?:\s*\((?:CNA|SUVA|INSAI|Suva)\))?|\b(?:CNA|INSAI|SUVA)\b")

EXTRACT_SYSTEM = """Du bist Jurist:in. Lies das Urteil und notiere stichwortartig (auf Deutsch):
1. Sachverhalt (2-3 Zeilen, ohne Namen), Vorinstanz und Partei, die Beschwerde führt.
2. Streitige Rechtsfrage(n).
3. Die tragenden Erwägungen: je eine Zeile pro Grundsatz, mit der exakten Erwägungsnummer aus dem Urteil
   (z.B. "E. 4.2: ..."). Zitiere zentrale Formulierungen wörtlich in Anführungszeichen.
4. Ergebnis (Dispositiv).
Erfinde nichts. Wenn eine Nummer nicht klar ist, lass sie weg."""


def _tokens(s):
    return [w for w in re.findall(r"[a-zäöüéèàç]{5,}", s.lower())]


def pick_examples(text, examples, lang, k=3):
    """Choose the k examples most similar to the judgement (simple tf-idf cosine)."""
    docs = [Counter(_tokens(ex[lang] + " " + ex["de"])) for ex in examples]
    df = Counter(w for d in docs for w in d)
    n = len(docs)

    def vec(c):
        return {w: tf * math.log((n + 1) / (df.get(w, 0) + 1)) for w, tf in c.items()}

    q = vec(Counter(_tokens(text[:15000])))
    qn = math.sqrt(sum(v * v for v in q.values())) or 1
    scored = []
    for ex, d in zip(examples, docs):
        v = vec(d)
        dot = sum(q.get(w, 0) * x for w, x in v.items())
        vn = math.sqrt(sum(x * x for x in v.values())) or 1
        scored.append((dot / (qn * vn), ex))
    scored.sort(key=lambda t: -t[0])
    return [ex for _, ex in scored[:k]]


def extract_notes(j):
    text = _excerpt(j.get("text") or "", config.LLM_MAX_INPUT_CHARS)
    return llm.chat([{"role": "system", "content": EXTRACT_SYSTEM},
                     {"role": "user", "content": f"Urteil {j['docket']}\n<judgement>\n{text}\n</judgement>"}],
                    temperature=0.1, max_tokens=1200)


def write_summary(j, notes, examples, lang, reference=None):
    shots = pick_examples((j.get("text") or "") + notes, examples, lang)
    shot_txt = "\n\n".join(f"Beispiel {i + 1} ({ex['docket']}):\n{ex[lang]}" for i, ex in enumerate(shots))
    target = "Deutsch" if lang == "de" else "Französisch (français)"
    label = "Erwägungen des Urteils" if lang == "de" else "Considérants de l'arrêt"
    valid = erwaegungen.numbers(j.get("text") or "")
    system = (f"Du verfasst für den Rechtsdienst der Suva Urteilszusammenfassungen auf {target}.\n\n"
              f"{STYLE[lang]}\n\n{GLOSSARY}")
    user = (f"Stilbeispiele echter Suva-Zusammenfassungen:\n\n{shot_txt}\n\n---\n"
            f"Notizen zum Urteil {j['docket']} vom {j.get('decision_date') or '?'}:\n{notes}\n\n"
            f"{label} (Nummer: Anfang des Texts):\n{erwaegungen.outline(j.get('text') or '', 120)}\n\n"
            f"Dispositiv des Urteils (verbindlich: das Ergebnis genau so wiedergeben; wer Beschwerde führte "
            f"und ob sie gutgeheissen, abgewiesen oder zurückgewiesen wurde):\n"
            f"{erwaegungen.dispositiv(j.get('text') or '')}\n\n"
            + (f"Bereits verfasste deutsche Zusammenfassung (gleiche Fakten, gleiches Ergebnis, gleiche Partei als "
               f"Beschwerdeführerin; nicht übersetzen, sondern eigenständig auf Französisch formulieren):\n{reference}\n\n"
               if reference else "") +
            f"Auszug aus dem Urteil (zur Kontrolle):\n<judgement>\n{(j.get('text') or '')[:6000]}\n</judgement>\n\n"
            f"Schreibe jetzt die Zusammenfassung auf {target}. Gib nur den Text der Zusammenfassung aus.")
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    text = llm.chat(msgs, temperature=0.3, max_tokens=900).strip()
    found, bad = erwaegungen.check_refs(text, valid)
    placeholder = PLACEHOLDER.search(text)
    if (valid and (bad or not found)) or placeholder:  # one corrective retry
        fix = ""
        if bad:
            fix += f"Die Nummern {', '.join(bad)} gibt es im Urteil nicht. Erlaubt sind nur: {', '.join(valid)}. "
        elif valid and not found:
            fix += f"Es fehlen Verweise auf die Erwägungen. Erlaubt sind nur: {', '.join(valid)}. "
        if placeholder:
            fix += "Entferne Platzhalter wie \"A.________\"; nenne die Parteien nach ihrer Rolle. "
        fix += "Gib die korrigierte Zusammenfassung aus, nur den Text."
        text = llm.chat(msgs + [{"role": "assistant", "content": text}, {"role": "user", "content": fix}],
                        temperature=0.2, max_tokens=900).strip()
        found, bad = erwaegungen.check_refs(text, valid)
    conflict = erwaegungen.outcome_conflict(text, j.get("text") or "")
    if conflict:  # the outcome must match the Dispositiv: one targeted correction
        real = {"admitted": "gutgeheissen / admis", "rejected": "abgewiesen / rejeté"}[erwaegungen.outcome(j.get("text") or "")]
        text = llm.chat(msgs + [{"role": "assistant", "content": text},
                                {"role": "user", "content": f"Falsches Ergebnis: \"{conflict}\". Laut Dispositiv wurde die Beschwerde vor "
                                                            f"Bundesgericht {real}. Korrigiere nur das, gib die ganze Zusammenfassung "
                                                            f"aus, nur den Text."}],
                        temperature=0.1, max_tokens=900).strip()
        found, bad = erwaegungen.check_refs(text, valid)
    words = len(text.split())
    if words > MAX_WORDS[lang] * 1.15:  # too long: one shortening pass, keeping the references
        short = ("Zu lang ({} Wörter). Kürze auf höchstens {} Wörter: nur Rechtsfrage, tragende Begründung und Ergebnis, "
                 "behalte die Erwägungsverweise, gleiche Sprache. Gib nur den Text aus.").format(words, MAX_WORDS[lang])
        shorter = llm.chat(msgs + [{"role": "assistant", "content": text}, {"role": "user", "content": short}],
                           temperature=0.1, max_tokens=700).strip()
        if shorter and len(shorter.split()) < words:
            text = shorter
            found, bad = erwaegungen.check_refs(text, valid)
    text = SUVA_ALIAS.sub("Suva", text)
    text = re.sub(r"\b([Ll])'Suva", lambda m: m.group(1) + "a Suva", text)  # l'INSAI -> la Suva
    text = PLACEHOLDER.sub("", text).replace(" ,", ",").replace("  ", " ")  # last resort for placeholders
    for nr in set(bad):  # last resort: never ship an invented reference
        text = re.sub(r"\s*\((?:E\.|Erw\.|consid\.)\s*" + re.escape(nr) + r"\)", "", text)
    return text


def summarize(j, examples):
    """Return {'de': text, 'fr': text, 'notes': notes}."""
    notes = extract_notes(j)
    de = write_summary(j, notes, examples, "de")
    # FR gets the DE text as a fact reference so both versions agree on who appealed and what was decided
    return {"notes": notes, "de": de, "fr": write_summary(j, notes, examples, "fr", reference=de)}
