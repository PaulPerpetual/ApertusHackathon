"""Controlled hashtag vocabulary for Suva's legal service: ~50 tags in 6 groups, DE + FR.

Tags describe WHY the court decided (the deciding legal ground), not generic topics. Apertus picks
from this list only (src/run_hashtags.py); finalize.py composes each card's tags as
  [subject area] [2-3 deciding grounds] [outcome]   (max 5; stored without '#', the UI adds it)
and writes tags (DE) and tags_fr (FR) in the same order (db.py contract).
"""
import json

from . import config, llm
from .triage import _excerpt

# group -> [(key, DE, FR)]
VOCAB = {
    "Unfall & Kausalität / Accident et causalité": [
        ("unfallbegriff", "#Unfallbegriff", "#notion-d-accident"),
        ("unfallaehnlich", "#unfallähnliche-Körperschädigung", "#lésion-assimilée"),
        ("kausal_nat", "#natürliche-Kausalität", "#causalité-naturelle"),
        ("kausal_adaeq", "#adäquate-Kausalität", "#causalité-adéquate"),
        ("psychisch", "#psychische-Unfallfolgen", "#troubles-psychiques"),
        ("hws", "#HWS-Schleudertrauma", "#traumatisme-cervical"),
        ("status_quo", "#Status-quo-ante", "#statu-quo-ante"),
        ("rueckfall", "#Rückfall-Spätfolgen", "#rechute-séquelles-tardives"),
        ("berufskrankheit", "#Berufskrankheit", "#maladie-professionnelle"),
        ("vorzustand", "#Vorzustand", "#état-antérieur"),
    ],
    "Leistungen UVG / Prestations LAA": [
        ("heilbehandlung", "#Heilbehandlung", "#traitement-médical"),
        ("pflege", "#Pflege-Hilflosigkeit", "#soins-impotence"),
        ("taggeld", "#Taggeld", "#indemnité-journalière"),
        ("verdienst", "#versicherter-Verdienst", "#gain-assuré"),
        ("rente", "#Invalidenrente-UVG", "#rente-d-invalidité-LAA"),
        ("ie", "#Integritätsentschädigung", "#indemnité-pour-atteinte-à-l-intégrité"),
        ("komplementaer", "#Komplementärrente-Überentschädigung", "#rente-complémentaire-surindemnisation"),
        ("fallabschluss", "#Fallabschluss", "#clôture-du-cas"),
        ("kuerzung", "#Leistungskürzung-Wagnis", "#réduction-des-prestations"),
        ("rueckforderung", "#Rückforderung", "#restitution"),
        ("versichert", "#Versicherteneigenschaft", "#qualité-d-assuré"),
        ("nbu", "#Nichtberufsunfall", "#accident-non-professionnel"),
        ("praemien", "#Prämien-Unterstellung", "#primes-assujettissement"),
    ],
    "Invalidität & Einkommen / Invalidité et revenus": [
        ("einkommensvergleich", "#Einkommensvergleich", "#comparaison-des-revenus"),
        ("lse", "#Tabellenlöhne-LSE", "#salaires-statistiques-ESS"),
        ("abzug", "#Leidensabzug", "#abattement"),
        ("valideneinkommen", "#Valideneinkommen", "#revenu-sans-invalidité"),
        ("verwertbarkeit", "#Verwertbarkeit-Restarbeitsfähigkeit", "#exigibilité-capacité-résiduelle"),
        ("au", "#Arbeitsunfähigkeit", "#incapacité-de-travail"),
        ("revision", "#Rentenrevision", "#révision-de-la-rente"),
        ("neuanmeldung", "#Neuanmeldung", "#nouvelle-demande"),
        ("schadenminderung", "#Schadenminderungspflicht", "#obligation-de-réduire-le-dommage"),
    ],
    "Abklärung & Beweis / Instruction et preuve": [
        ("gutachten", "#Beweiswert-Gutachten", "#valeur-probante-expertise"),
        ("zweitgutachten", "#Gutachterwahl-Zweitgutachten", "#choix-de-l-expert-seconde-expertise"),
        ("interne_aerzte", "#versicherungsinterne-Ärzte", "#médecins-internes"),
        ("untersuchung", "#Untersuchungsgrundsatz", "#maxime-inquisitoire"),
        ("beweiswuerdigung", "#Beweiswürdigung-Einzelfall", "#appréciation-des-preuves"),
    ],
    "Verfahren / Procédure": [
        ("gehoer", "#rechtliches-Gehör", "#droit-d-être-entendu"),
        ("emrk", "#öffentliche-Verhandlung-EMRK", "#débats-publics-CEDH"),
        ("rechtskraft", "#Rechtskraft-Wiedererwägung", "#force-de-chose-jugée-reconsidération"),
        ("fristen", "#Fristen-Zustellung", "#délais-notification"),
        ("legitimation", "#Legitimation-Vertretung", "#qualité-pour-recourir-représentation"),
        ("nichteintreten", "#Nichteintreten", "#irrecevabilité"),
        ("verzoegerung", "#Rechtsverzögerung", "#déni-de-justice"),
        ("kosten", "#Parteientschädigung-Kosten", "#dépens-frais"),
        ("upr", "#unentgeltliche-Rechtspflege", "#assistance-judiciaire"),
        ("koordination", "#Koordination-Sozialversicherungen", "#coordination-assurances-sociales"),
        ("regress", "#Regress", "#recours-contre-tiers"),
    ],
    "Ergebnis / Issue": [
        ("gutheissung", "#gutgeheissen", "#admis"),
        ("teilweise", "#teilweise-gutgeheissen", "#partiellement-admis"),
        ("abweisung", "#abgewiesen", "#rejeté"),
        ("rueckweisung", "#Rückweisung-zur-Abklärung", "#renvoi-pour-instruction"),
    ],
}
OUTCOME_GROUP = "Ergebnis / Issue"
BY_KEY = {k: (de, fr, g) for g, items in VOCAB.items() for k, de, fr in items}
AREA = {"accident": ("#UVG", "#LAA"), "invalidity": ("#IV", "#AI"), "daily_allowance": ("#Taggeldversicherung", "#assurance-perte-de-gain")}
SUVA_PARTY = ("#SuvaPartei", "#Suva-partie")


def vocabulary():
    """Grouped vocabulary for the UI (GET /api/hashtags)."""
    return [{"group": g, "tags": [{"key": k, "de": de.lstrip("#"), "fr": fr.lstrip("#")} for k, de, fr in items]}
            for g, items in VOCAB.items()]


SYSTEM = """Du bist Jurist:in im Rechtsdienst der Suva. Ordne ein Urteil des Bundesgerichts mit Schlagworten aus einer
FESTEN Liste ein, damit Kolleg:innen Urteile nach dem tragenden Entscheidungsgrund finden.

Regeln:
- Wähle 2 bis 3 Schlüssel für die TRAGENDEN GRÜNDE: worauf das Bundesgericht seinen Entscheid stützt
  (nicht bloss Themen, die erwähnt werden). Der wichtigste zuerst.
- Wähle genau 1 Schlüssel für das ERGEBNIS (gutheissung, teilweise, abweisung, rueckweisung, nichteintreten).
- Nur Schlüssel aus der Liste verwenden.

Liste (Schlüssel = Bedeutung):
{vocab}

Antworte ausschliesslich mit JSON: {{"gruende": ["<key>", "<key>"], "ergebnis": "<key>"}}"""


def _vocab_text():
    return "\n".join(f"[{g}] " + ", ".join(f"{k} = {de[1:]}" for k, de, _ in items) for g, items in VOCAB.items())


def choose(j, explanation=""):
    """Ask Apertus for 2-3 deciding-ground keys + 1 outcome key. Unknown keys are dropped."""
    user = (f"Urteil {j['docket']} (Rechtsgebiet: {j.get('subject') or '?'})\n"
            f"Kurzbeurteilung: {explanation}\n\n<judgement>\n{_excerpt(j.get('text') or '', min(16000, config.LLM_MAX_INPUT_CHARS))}\n</judgement>")
    out = llm.chat([{"role": "system", "content": SYSTEM.format(vocab=_vocab_text())}, {"role": "user", "content": user}],
                   temperature=0.0, max_tokens=150, json_mode=True)
    a = llm.parse_json(out)
    grounds = [k for k in (a.get("gruende") or []) if k in BY_KEY and BY_KEY[k][2] != OUTCOME_GROUP][:3]
    outcome = a.get("ergebnis") if a.get("ergebnis") in BY_KEY else None
    return {"grounds": list(dict.fromkeys(grounds)), "outcome": outcome}


def compose(areas, grounds, outcome):
    """-> (tags_de, tags_fr), same order, max 5, WITHOUT the leading '#' (the UI adds it).
    Suva as a party is not a tag: the UI shows its own badge from the suva_party field."""
    pairs = [AREA[a] for a in areas if a in AREA][:1]
    pairs += [BY_KEY[k][:2] for k in grounds if k in BY_KEY]
    if outcome in BY_KEY:
        pairs.append(BY_KEY[outcome][:2])
    seen, out = set(), []
    for de, fr in pairs:
        if de not in seen:
            seen.add(de)
            out.append((de.lstrip("#"), fr.lstrip("#")))
    out = out[:5]
    return [p[0] for p in out], [p[1] for p in out]


def dumps(x):
    return json.dumps(x, ensure_ascii=False)
