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
Invalidenrente ↔ rente d'invalidité | Invaliditätsgrad ↔ taux d'invalidité | Valideneinkommen ↔ revenu sans invalidité
Invalideneinkommen ↔ revenu d'invalide | Tabellenlohn (LSE) ↔ salaire statistique (ESS) | Leidensabzug ↔ abattement
Integritätsentschädigung ↔ indemnité pour atteinte à l'intégrité | Taggeld ↔ indemnité journalière
natürlicher/adäquater Kausalzusammenhang ↔ lien de causalité naturelle/adéquate | Rückfall ↔ rechute
Spätfolgen ↔ séquelles tardives | Berufskrankheit ↔ maladie professionnelle | Heilbehandlung ↔ traitement médical
Fallabschluss ↔ clôture du cas | Rentenrevision ↔ révision de la rente | Gutachten ↔ expertise
rechtliches Gehör ↔ droit d'être entendu | öffentliche Verhandlung ↔ débats publics | Vorinstanz ↔ autorité précédente
Kantonsgericht/Versicherungsgericht ↔ tribunal cantonal des assurances | gutheissen ↔ admettre | abweisen ↔ rejeter
zurückweisen ↔ renvoyer | Nichteintreten ↔ irrecevabilité"""

STYLE = {
    "de": """Stil der Suva-Zusammenfassungen (Deutsch):
- 120-300 Wörter, 1-4 Absätze, sachlicher Fliesstext, keine Aufzählungen, keine Überschriften.
- Entweder mit dem Sachverhalt in einem Satz beginnen ("Versicherter, Maurer, der ...") oder direkt mit dem
  Rechtsgrundsatz ("Erwartet der Versicherer ..., muss er ...").
- Kern sind die Grundsätze und die Begründung des Bundesgerichts, mit Verweis auf die Erwägung in Klammern
  "(Erw. 5.2)". Nur Erwägungsnummern verwenden, die in den Notizen stehen.
- Bundesgericht als "das Bundesgericht" oder "das BGer". Ergebnis am Schluss nennen
  ("Das Bundesgericht wies die Beschwerde ab." / "hiess die Beschwerde gut").
- Keine Personennamen und keine Platzhalter wie "A.________"; Parteien als "der Versicherte",
  "die Beschwerdeführerin", "die Suva".
- Jeder Absatz verweist mindestens einmal auf die tragende Erwägung im Format "(E. 5.2)" oder "(E. 4.3.1 und 4.3.2)".
  Nur Nummern aus der Liste "Erwägungen des Urteils" verwenden.""",
    "fr": """Style des résumés de la Suva (français):
- 120-300 mots, 1-4 paragraphes, texte suivi et factuel, pas d'énumérations ni de titres.
- Commencer soit par les faits en une phrase ("Assuré, carreleur, qui ...") soit directement par le principe
  ("Lorsque l'assureur attend ..., il doit ...").
- L'essentiel: les principes et le raisonnement du Tribunal fédéral, avec renvoi au considérant entre
  parenthèses "(consid. 5.2)". N'utiliser que des numéros de considérants figurant dans les notes.
- "le Tribunal fédéral" ou "le TF". Indiquer l'issue à la fin ("Le Tribunal fédéral a rejeté le recours.").
- Pas de noms de personnes ni de caractères de substitution comme "A.________"; parties: "l'assuré",
  "la recourante", "la Suva".
- Chaque paragraphe renvoie au moins une fois au considérant déterminant, au format "(consid. 5.2)" ou
  "(consid. 4.3.1 et 4.3.2)". N'utiliser que des numéros de la liste "Considérants de l'arrêt".
- Rédiger directement en français juridique suisse, ce n'est pas une traduction de l'allemand.""",
}

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


def write_summary(j, notes, examples, lang):
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
    text = PLACEHOLDER.sub("", text).replace(" ,", ",").replace("  ", " ")  # last resort for placeholders
    for nr in set(bad):  # last resort: never ship an invented reference
        text = re.sub(r"\s*\((?:E\.|Erw\.|consid\.)\s*" + re.escape(nr) + r"\)", "", text)
    return text


def summarize(j, examples):
    """Return {'de': text, 'fr': text, 'notes': notes}."""
    notes = extract_notes(j)
    return {"notes": notes, "de": write_summary(j, notes, examples, "de"),
            "fr": write_summary(j, notes, examples, "fr")}
