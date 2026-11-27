"""Checks after Apertus has written a summary or a relevance reason (docs/analysis of the 54 Suva examples).

Two kinds of tools:
* problems(...) -> list of short instructions for one targeted retry (the model fixes its own text);
* clean_summary(...) / clean_reason(...) -> mechanical, meaning-preserving fixes that are always safe to apply,
  also at display time on texts already in the DB (table remnants, citations in the wrong language,
  cost/"Obsiegen" sentences, reasons cut off mid-sentence).
"""
import re

SENT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜÉÈÀ«\"(])")

COST = re.compile(r"Gerichtskosten|Parteientschädigung|Parteikosten|Kostenfolge|\bObsiegen|\bobsiegt|"
                  r"frais judiciaires|\bdépens\b|\bFr\.\s?\d|\b\d[\d']*\s?(?:fr\.|francs)|\bCHF\b", re.I)
TABLE_CELL = re.compile(r"(?:Condition|Voraussetzung|Portée|Tragweite|Status|Statut|Principe|Grundsatz|Rechtssatz|"
                        r"Obligation|E\.\s*\d|consid\.|Art\.|ja\b|oui\b|nein\b|non\b|admis|bejaht|verneint|rejet)", re.I)
MONTHS = ("Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|"
          "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre")
DATE = re.compile(r"\b\d{1,2}\.?\s?(?:er\s)?(?:" + MONTHS + r")\b|\b\d{1,2}\.\d{1,2}\.(?:19|20)\d\d\b", re.I)
BIRTH = re.compile(r"\bJahrgang\b|\bgeboren\b|\bné(?:e)? en\b", re.I)
CITES = re.compile(r"\b(?:BGE|ATF|DTF)\s+\d+\s+[IV]+\s+\d+|\b\d[A-Z]_\d+/\d{4}")

NON_UV_SUBJECT = re.compile(r"Invaliden|invalidit|AHV|\bAVS\b|BVG|\bLPP\b|berufliche Vorsorge|prévoyance|Kranken|"
                            r"maladie|Ergänzungsleistung|prestations complémentaires|Arbeitslos|chômage", re.I)
UV_SUBJECT = re.compile(r"Unfall|accident|infortuni", re.I)
UV_IN_TEXT = re.compile(r"Unfallversicher|assurance-accidents|assureur-accidents|\bSuva\b|\bSUVA\b|\bCNA\b|"
                        r"Unfallversicherungsanstalt|Caisse nationale suisse d'assurance", re.I)
UV_IN_OUT = re.compile(r"Unfallversicherer|\bSuva\b|assureur-accidents|assurance-accidents", re.I)

# words that only appear when Apertus mistranslates (from the review of the 54 examples)
BLOCK = {
    "de": {"Gefahrengemeinschaft": "Wagnis (relatives/absolutes Wagnis)",
           "Bandagenverletzung": "Bandverletzung", "private Haftstrafe": "Untersuchungshaft / Freiheitsentzug",
           "OPGA": "ATSG", "Toluin": "Toluol", "IPAI": "Integritätsentschädigung (IE)",
           "IPIA": "Integritätsentschädigung (IE)"},
    "fr": {"communauté de risque": "entreprise téméraire"},
}


def _sentences(text):
    return [s for s in SENT.split(text.strip()) if s]


def _strip_cites(text):
    return CITES.sub("", text)


def outcome_problem(out, text):
    """The Dispositiv rejects the appeal entirely, but the summary says (partly) admitted or remanded."""
    from . import erwaegungen
    if erwaegungen.outcome(text) != "rejected" or re.search(r"teilweise|partiellement|surplus|Übrigen",
                                                           erwaegungen.dispositiv(text, 300), re.I):
        return None
    lower = re.compile(r"kantonal|Vorinstanz|Versicherungsgericht|tribunal cantonal|cour cantonale|autorité précédente|"
                       r"juridiction (?:cantonale|précédente)|premiers juges|IV-Stelle|office AI|\d[A-Z]_\d+/\d{4}", re.I)
    for sent in _sentences(out):
        for clause in re.split(r";|,\s+(?:und|et)\s+", sent):
            if lower.search(clause):
                continue
            if (re.search(r"Beschwerde|recours", clause, re.I) and re.search(r"gutgeheissen|gutgeheißen|\badmis\b", clause, re.I)) \
                    or re.search(r"(?:wird|werden)\s[^.]{0,120}zurückgewiesen|(?:est|sont)\s+renvoyée?s?\b", clause, re.I):
                return sent
    return None


META = re.compile(r"^\s*(?:Keine Korrektur|Der Text bleibt|Korrigierte?r? (?:Text|Fassung)\s*:|Hier ist|Voici|Aucune correction|"
                  r"Le texte reste)", re.I)


def better(old, new, j, lang):
    """Accept a model's correction only if it is a real summary and has fewer problems than before."""
    if not new or META.search(new) or len(new.split()) < 0.4 * len(old.split()) or len(new.split()) > 1.6 * len(old.split()) + 40:
        return False
    return len(problems(new, j, lang)) < len(problems(old, j, lang)) or not problems(new, j, lang)


def reason_problems(text_de, text_fr, j):
    """Checks for the short relevance reason ("Begründung")."""
    from . import tags
    p = []
    if text_de and not tags.lang_ok(text_de, "de"):
        p.append("DE muss Deutsch sein")
    if text_fr and not tags.lang_ok(text_fr, "fr"):
        p.append("FR doit être en français")
    subject, text = j.get("subject") or "", j.get("text") or ""
    if NON_UV_SUBJECT.search(subject) and not UV_SUBJECT.search(subject) and not UV_IN_TEXT.search(text) \
            and UV_IN_OUT.search((text_de or "") + " " + (text_fr or "")):
        p.append("die Suva/ein Unfallversicherer ist NICHT Partei (" + subject.strip(" ,") + "): nicht schreiben "
                 "'die Suva muss', sondern welcher Rechtssatz sich auf die Unfallversicherung übertragen lässt")
    for t in (text_de, text_fr):
        if t and len(t.split()) > 45:
            p.append("höchstens 40 Wörter pro Sprache")
            break
    return p


def problems(out, j, lang, words=None):
    """Instructions for one correction round; [] if the text passes."""
    from . import tags
    text = j.get("text") or ""
    subject = j.get("subject") or ""
    p = []
    if not tags.lang_ok(out, lang):
        p.append("der GANZE Text muss auf " + ("Deutsch" if lang == "de" else "Französisch (en français)")
                 + " sein, nichts in der anderen Sprache")
    wrong = outcome_problem(out, text)
    if wrong:
        p.append(f"falsches Ergebnis: \"{wrong[:160]}\" – laut Dispositiv wurde die Beschwerde vollständig ABGEWIESEN "
                 f"(keine Gutheissung, keine Rückweisung)")
    if re.search(r"Dispositiv|dispositif", out):
        p.append("das Dispositiv nicht erwähnen")
    if " | " in out:
        p.append("keine Tabelle und keine Trennstriche '|': nur Fliesstext in ganzen Sätzen")
    if COST.search(out):
        p.append("keine Gerichtskosten, Parteientschädigungen, Beträge und keine Sätze über Obsiegen/Unterliegen")
    if DATE.search(_strip_cites(out)) or BIRTH.search(out):
        p.append("keine Daten, Geburtsjahre oder Altersangaben")
    if re.search(r"(?<![/\d])(?<!LSE )(?<!ESS )(?:19|20)\d\d(?![/\d])", _strip_cites(out)):
        p.append("keine Jahreszahlen (ausser in Zitaten von Urteilen)")
    if NON_UV_SUBJECT.search(subject) and not UV_SUBJECT.search(subject) and not UV_IN_TEXT.search(text) \
            and UV_IN_OUT.search(out):
        p.append("in diesem Urteil ist KEIN Unfallversicherer Partei (Rechtsgebiet: " + subject.strip(" ,")
                 + "): die beteiligte Stelle mit ihrer Funktion bezeichnen (z.B. 'die IV-Stelle' / 'l'office AI'); "
                   "die Unfallversicherung nicht erwähnen")
    if lang == "de" and re.search(r"\bconsid\.|\bATF\b|\barrêts?\b|\bcf\.\s", out):
        p.append("Zitate auf Deutsch: 'BGE … E. …', 'Urteil 8C_…', nicht 'ATF', 'consid.', 'arrêt'")
    if lang == "fr" and re.search(r"\bBGE\b|\(E\.\s*\d|;\s*E\.\s*\d|\bUrteils?\b|\bErw\.", out):
        p.append("citations en français: 'ATF … consid. …', 'arrêt 8C_…', pas 'BGE', 'E.', 'Urteil'")
    for bad, good in BLOCK[lang].items():
        if bad.lower() in out.lower():
            p.append(f"'{bad}' ist falsch, richtig: {good}")
    if re.search(r"(?:gilt|gelten) (?:auch|ebenso) (?:für die|im Bereich der|in der) Unfallversicherung|applicable (?:aussi |également )?à l'assurance-accidents"
                 r"|Portée\s*:|Tragweite\s*:", out, re.I):
        p.append("keine Meta-Sätze über die Übertragbarkeit ('gilt auch für die Unfallversicherung'), nur den Rechtssatz")
    if words and len(out.split()) > words:
        p.append(f"höchstens {words} Wörter")
    return p


def clean_summary(out, lang):
    """Mechanical fixes that never change the legal content."""
    if not out:
        return out
    paras = []
    for para in out.split("\n"):
        if "|" in para:  # extraction table leaked into the text: keep the real sentences, drop the cells
            segs = [x.strip() for x in re.split(r"\s*\|\s*", para) if x.strip()]
            keep = [x for x in segs if len(x.split()) >= 8 and not TABLE_CELL.match(x)] or segs[:1]
            para = ""
            for x in keep:
                para = (para + (" " if re.search(r"[.!?;:]$", para) else ", ") + x) if para else x
            if para and not re.search(r"[.!?)»\"]$", para):
                para += "."
        para = " ".join(s for s in _sentences(para) if not COST.search(s)) if para.strip() else para
        para = re.sub(r"\s*(?:und|et|;)?\s*(?:Dispositiv|dispositif)(?:-Ziff\.|\s+ch\.)?\s*\d*(?=\))", "", para)
        paras.append(para)
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(paras)).strip()
    out = re.sub(r"(\b(?:E\.|consid\.)\s*\d[\d.]*)\s+(?:des Urteils|de l'arrêt)", r"\1", out)
    if lang == "de":
        out = re.sub(r"\bATF\s+(\d+\s+[IV]+\s+\d+)", r"BGE \1", out)
        out = re.sub(r"\bconsid\.\s*(?=\d)", "E. ", out)
        out = re.sub(r"\barrêts\s+(?=\d[A-Z]_)", "Urteile ", out)
        out = re.sub(r"\barrêt\s+(?=\d[A-Z]_)", "Urteil ", out)
        out = re.sub(r"(\d[A-Z]_\d+/\d{4}(?:\s+E\.\s*[\d.]+)?)\s+et\s+(?=\d[A-Z]_)", r"\1 und ", out)
    else:
        out = re.sub(r"\bBGE\s+(\d+\s+[IV]+\s+\d+)", r"ATF \1", out)
        out = re.sub(r"(?<=[(;,]\s)E\.\s*(?=\d)|(?<=[(;,])E\.\s*(?=\d)|(?<=ATF \d{3} [IV] \d{3} )E\.\s*(?=\d)", "consid. ", out)
        out = re.sub(r"\bUrteile\s+(?=\d[A-Z]_)", "arrêts ", out)
        out = re.sub(r"\bUrteil\s+(?=\d[A-Z]_)", "arrêt ", out)
    return out


def clean_reason(text, max_words=45):
    """Reasons ("Begründung"): drop an unfinished last sentence and cap the length at whole sentences."""
    if not text:
        return text
    t = re.sub(r"^\s*(?:Für die Suva|Pour la Suva)\s*:\s*", "", text.strip())
    t = re.sub(r"(?:Für die Suva bedeutet dies|Bedeutung für (?:die )?Suva|Für (?:die )?Suva)\s*:\s*(\w)",
               lambda m: m.group(1).upper(), t)
    t = re.sub(r"\s+", " ", t)
    sents = _sentences(t)
    if sents and (not re.search(r"[.!?)»\"]$", sents[-1]) or re.search(r"\b\d{1,2}\.$", sents[-1])):
        if len(sents) > 1:
            sents = sents[:-1]
        else:  # single unfinished sentence: end it at the last complete clause
            s = re.sub(r"[;,–-]?\s*[^;,–]*$", "", sents[0]) if re.search(r"[;,–]", sents[0]) else sents[0]
            sents = [s.rstrip(" ;,–") + "."]
    keep, n = [], 0
    for s in sents:
        w = len(s.split())
        if keep and max_words and n + w > max_words:
            break
        keep.append(s)
        n += w
    return " ".join(keep) if keep else t
