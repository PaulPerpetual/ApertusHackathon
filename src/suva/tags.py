"""Fixed Suva keyword list ("Schlagworte"): what the legal service filters by.

Topics only, no outcome ("abgewiesen", "Nichteintreten" ...) and no catch-alls ("Beweiswürdigung-Einzelfall").
Each entry: German label (the key, stored in the DB), French label, and patterns that map the model's
free-form tags onto it. The model is asked to pick from this list; older free-form tags are mapped at read time.
"""
import re

VOCAB = [
    # (DE label, FR label, regex on the normalised free tag)
    ("UVG", "LAA", r"^(uvg|laa|unfallversicherung|assurance accidents|assicurazione contro gli infortuni)$"),
    ("IV", "AI", r"^(iv|ai|ivg|lai|invalidenversicherung|assurance invalidit|assicurazione per l.?invalidit)"),
    # neighbouring social insurances: matter to Suva for coordination, named as areas like the court does
    ("BVG", "LPP", r"^(bvg|lpp|berufliche vorsorge|prévoyance professionnelle|previdenza professionale)"),
    ("KVG", "LAMal", r"^(kvg|lamal|krankenversicherung|assurance maladie|assicurazione malattia)"),
    ("ALV", "AC", r"^(alv|avig|arbeitslosenversicherung|assurance chômage|assicurazione contro la disoccupazione)"),
    ("AHV / EL", "AVS / PC", r"^(ahv|avs|alters und hinterlassenen|assurance vieillesse|ergänzungsleistung|prestations? complémentaire)"),
    ("Militärversicherung", "Assurance militaire", r"^(mvg|militärversicherung|assurance militaire)"),
    ("Unfallbegriff", "Notion d'accident", r"unfallbegriff|ungewöhnlich.*äusser|notion d.?accident"),
    ("Natürliche Kausalität", "Causalité naturelle", r"natürlich.*kausal|causalit.*naturel|nesso causale naturale"),
    ("Adäquate Kausalität", "Causalité adéquate", r"adäquat|causalit.*adéquat|nesso causale adeguato"),
    ("Vorzustand / Status quo ante", "État antérieur / statu quo ante", r"status quo|vorzustand|statu quo|état antérieur|vorbestehend"),
    ("Rückfall / Spätfolgen", "Rechute / séquelles tardives", r"rückfall|spätfolge|rechute|séquelle|ricaduta"),
    ("Berufskrankheit", "Maladie professionnelle", r"berufskrankheit|maladie professionnelle"),
    ("Unfallähnliche Körperschädigung", "Lésion assimilée à un accident", r"unfallähnlich|listenverletzung|lésion.*assimilée|art\.? ?6 ?abs\.? ?2"),
    ("Psychische Unfallfolgen", "Troubles psychiques", r"psych"),
    ("HWS / Schleudertrauma", "Traumatisme cervical", r"hws|schleuder|whiplash|cervical"),
    ("Heilbehandlung", "Traitement médical", r"heilbehandlung|traitement médical|heilungskosten"),
    ("Taggeld", "Indemnités journalières", r"taggeld|indemnit.*journali|indennit.*giornalier"),
    ("Invalidenrente", "Rente d'invalidité", r"invalidenrente|rente d.?invalidit|rendita d.?invalidit|rentenanspruch|komplementärrente|rente complémentaire"),
    ("Einkommensvergleich", "Comparaison des revenus", r"einkommensvergleich|comparaison des revenus|confronto dei redditi|invaliditätsgrad|taux d.?invalidit|grado d.?invalidit"),
    ("Valideneinkommen", "Revenu sans invalidité", r"valideneinkommen|revenu sans invalidit|reddito da valido"),
    ("Invalideneinkommen / LSE", "Revenu d'invalide / ESS", r"invalideneinkommen|tabellenl|\blse\b|\bess\b|revenu d.?invalide|reddito da invalido"),
    ("Leidensabzug", "Abattement", r"leidensabzug|abattement"),
    ("Zumutbarkeit / Verwertbarkeit", "Exigibilité", r"zumutbar|verwertbar|restarbeitsf|arbeitsfähigkeit|exigib|capacité de travail"),
    ("Integritätsentschädigung", "Indemnité pour atteinte à l'intégrité", r"integrität|intégrité|integrità"),
    ("Hilflosenentschädigung", "Allocation pour impotent", r"hilflos|impotent"),
    ("Rentenrevision", "Révision de la rente", r"revision|révision"),
    ("Leistungskürzung", "Réduction des prestations", r"kürzung|wagnis|grobfahrl|réduction|entreprise téméraire"),
    ("Rückforderung", "Restitution", r"rückforderung|restitution"),
    ("Koordination", "Coordination", r"koordination|coordination|überentschädigung|surindemnisation"),
    ("Versicherteneigenschaft", "Qualité d'assuré", r"versichertenei|versicherungsdeckung|nachdeckung|qualité d.?assuré|couverture d.?assurance"),
    ("Beweiswert Gutachten", "Valeur probante des expertises", r"gutachten|expertise|beweiswert|valeur probante"),
    ("Untersuchungsgrundsatz", "Maxime inquisitoire", r"untersuchungsgrundsatz|maxime inquisitoire|ungenügend abgekl|instruction insuffisante"),
    ("Rechtliches Gehör", "Droit d'être entendu", r"rechtliches gehör|droit d.?être entendu"),
    ("Öffentliche Verhandlung (EMRK)", "Débats publics (CEDH)", r"verhandlung|emrk|cedh|débats publics"),
    ("Verfahren / Fristen", "Procédure / délais", r"frist|zustellung|verfahrensfrage|délai|legitimation|vertretung|nichteintreten|irrecevabilit"),
    ("Kosten / Parteientschädigung", "Frais / dépens", r"kosten|parteientsch|dépens|frais|unentgeltlich|assistance judiciaire"),
]
FR = {de: fr for de, fr, _ in VOCAB}
AREAS = ["UVG", "IV", "BVG", "KVG", "ALV", "AHV / EL", "Militärversicherung"]
PROCEDURAL = {"Untersuchungsgrundsatz", "Rechtliches Gehör", "Öffentliche Verhandlung (EMRK)", "Verfahren / Fristen",
              "Kosten / Parteientschädigung"}
MAX_TAGS = 5
_COMPILED = [(de, re.compile(p, re.I)) for de, _, p in VOCAB]


# Wording rules shared by triage and relabel: write like Suva's legal service does.
LANGUAGE_RULES = """Sprache und Stil (wie im Rechtsdienst der Suva):
- Fachsprache des Sozialversicherungsrechts, sachlich und knapp; keine Umgangssprache, keine Wertungen wie "wichtig" oder "spannend".
- Deutsch: "das Bundesgericht" (BGer), "die versicherte Person"/"der Versicherte", "die Suva", "die Vorinstanz";
  Normen als "Art. 6 Abs. 1 UVG", "Art. 17 ATSG"; Begriffe wie natürlicher/adäquater Kausalzusammenhang,
  Status quo ante/sine, Integritätsentschädigung, Invaliditätsgrad, Valideneinkommen, Invalideneinkommen, Tabellenlohn (LSE).
- Français: "le Tribunal fédéral" (TF), "l'assuré(e)", "la Suva", "l'autorité précédente"; normes "art. 6 al. 1 LAA",
  "art. 17 LPGA"; termes: lien de causalité naturelle/adéquate, statu quo ante/sine, indemnité pour atteinte à l'intégrité,
  taux d'invalidité, revenu sans invalidité, revenu d'invalide, salaire statistique (ESS).
- Erlasse mit der Abkürzung der jeweiligen Sprache: UVG/LAA, UVV/OLAA, IVG/LAI, IVV/RAI, ATSG/LPGA, ATSV/OPGA, BVG/LPP;
  nie italienische Abkürzungen (OAI, LAINF, OAINF) in einem deutschen oder französischen Text.
- Jedes Feld strikt in seiner Sprache (_de = Deutsch, _fr = Français), unabhängig von der Sprache des Urteils.
- Keine Personennamen und keine Platzhalter wie "A.________"."""


def _norm(tag):
    return re.sub(r"\s+", " ", str(tag).replace("-", " ").replace("_", " ")).strip().lower()


def normalize(tags):
    """Map free-form model tags onto the fixed list (keeps order, drops duplicates, outcomes and catch-alls)."""
    out = []
    for t in tags or []:
        n = _norm(t)
        for de, rx in _COMPILED:
            if rx.search(n):
                if de not in out:
                    out.append(de)
                break
    return out


def french(tags):
    """French labels; tags outside the list (added by hand) stay as written."""
    return [FR.get(t, t) for t in tags]


def vocab():
    return [{"de": de, "fr": fr} for de, fr, _ in VOCAB]


def prompt_list():
    return ", ".join(de for de, _, _ in VOCAB)


_LANG_WORDS = {
    "de": re.compile(r"\b(der|die|das|und|ist|nicht|wird|zur|zum|des|vom|auf|für)\b", re.I),
    "fr": re.compile(r"\b(le|la|les|des|du|une|est|selon|pour|dans|qui|que)\b|\b[ld]'", re.I),
    "it": re.compile(r"\b(il|della|delle|che|del|non|per|sono|alla|dell|gli|nella)\b", re.I),
}


def lang_ok(text, lang):
    """Cheap guard: True if `text` reads like `lang` (de/fr) and not like one of the other two languages.
    Short strings (titles) without enough function words pass."""
    counts = {k: len(rx.findall(text or "")) for k, rx in _LANG_WORDS.items()}
    if sum(counts.values()) < 3:
        return True
    return counts[lang] >= max(v for k, v in counts.items() if k != lang)


def combine(ai, subject):
    """Tags for a ruling: the area(s) from the court's subject line first (it is reliable), then the model's legal
    topics, then the court's topics. Procedural tags only on social-insurance rulings (otherwise they flood the
    filter with criminal and civil cases) and after the substantive ones; at most MAX_TAGS."""
    court = normalize(re.split(r"[();,]", subject or ""))
    model = normalize(ai)
    areas = [t for t in court + model if t in AREAS]
    topics = [t for t in model + court if t not in AREAS and t not in PROCEDURAL]
    proc = [t for t in model + court if t in PROCEDURAL] if areas else []
    out = []
    for t in areas + topics + proc:
        if t not in out:
            out.append(t)
    return out[:MAX_TAGS]
