"""Fixed Suva keyword list ("Schlagworte"): what the legal service filters by.

Topics only, no outcome ("abgewiesen", "Nichteintreten" ...) and no catch-alls ("Beweiswürdigung-Einzelfall").
Each entry: German label (the key, stored in the DB), French label, and patterns that map the model's
free-form tags onto it. The model is asked to pick from this list; older free-form tags are mapped at read time.
"""
import re

VOCAB = [
    # (DE label, FR label, regex on the normalised free tag)
    ("UVG", "LAA", r"^(uvg|laa|unfallversicherung|assurance accidents)$"),
    ("IV", "AI", r"^(iv|ai|ivg|lai|invalidenversicherung|assurance invalidit)"),
    ("Unfallbegriff", "Notion d'accident", r"unfallbegriff|ungewöhnlich.*äusser|notion d.?accident"),
    ("Natürliche Kausalität", "Causalité naturelle", r"natürlich.*kausal|causalit.*naturel"),
    ("Adäquate Kausalität", "Causalité adéquate", r"adäquat|causalit.*adéquat"),
    ("Vorzustand / Status quo ante", "État antérieur / statu quo ante", r"status quo|vorzustand|statu quo|état antérieur|vorbestehend"),
    ("Rückfall / Spätfolgen", "Rechute / séquelles tardives", r"rückfall|spätfolge|rechute|séquelle"),
    ("Berufskrankheit", "Maladie professionnelle", r"berufskrankheit|maladie professionnelle"),
    ("Unfallähnliche Körperschädigung", "Lésion assimilée à un accident", r"unfallähnlich|listenverletzung|lésion.*assimilée|art\.? ?6 ?abs\.? ?2"),
    ("Psychische Unfallfolgen", "Troubles psychiques", r"psych"),
    ("HWS / Schleudertrauma", "Traumatisme cervical", r"hws|schleuder|whiplash|cervical"),
    ("Heilbehandlung", "Traitement médical", r"heilbehandlung|traitement médical|heilungskosten"),
    ("Taggeld", "Indemnités journalières", r"taggeld|indemnit.*journali"),
    ("Invalidenrente", "Rente d'invalidité", r"invalidenrente|rente d.?invalidit|rentenanspruch|komplementärrente|rente complémentaire"),
    ("Einkommensvergleich", "Comparaison des revenus", r"einkommensvergleich|comparaison des revenus|invaliditätsgrad|taux d.?invalidit"),
    ("Valideneinkommen", "Revenu sans invalidité", r"valideneinkommen|revenu sans invalidit"),
    ("Invalideneinkommen / LSE", "Revenu d'invalide / ESS", r"invalideneinkommen|tabellenl|\blse\b|\bess\b|revenu d.?invalide"),
    ("Leidensabzug", "Abattement", r"leidensabzug|abattement"),
    ("Zumutbarkeit / Verwertbarkeit", "Exigibilité", r"zumutbar|verwertbar|restarbeitsf|arbeitsfähigkeit|exigib|capacité de travail"),
    ("Integritätsentschädigung", "Indemnité pour atteinte à l'intégrité", r"integrität|intégrité"),
    ("Hilflosenentschädigung", "Allocation pour impotent", r"hilflos|impotent"),
    ("Rentenrevision", "Révision de la rente", r"revision|révision"),
    ("Leistungskürzung", "Réduction des prestations", r"kürzung|wagnis|grobfahrl|réduction|entreprise téméraire"),
    ("Rückforderung", "Restitution", r"rückforderung|restitution"),
    ("Koordination", "Coordination", r"koordination|coordination|überentschädigung|surindemnisation"),
    ("Versicherteneigenschaft", "Qualité d'assuré", r"versichertenei|versicherungsdeckung|nachdeckung|qualité d.?assuré|couverture d.?assurance"),
    ("Beweiswert Gutachten", "Valeur probante des expertises", r"gutachten|expertise|beweiswert|valeur probante"),
    ("Untersuchungsgrundsatz", "Maxime inquisitoire", r"untersuchungsgrundsatz|abklärung|maxime inquisitoire|instruction"),
    ("Rechtliches Gehör", "Droit d'être entendu", r"rechtliches gehör|droit d.?être entendu"),
    ("Öffentliche Verhandlung (EMRK)", "Débats publics (CEDH)", r"verhandlung|emrk|cedh|débats publics"),
    ("Verfahren / Fristen", "Procédure / délais", r"frist|zustellung|verfahren|délai|procédure|legitimation|vertretung"),
    ("Kosten / Parteientschädigung", "Frais / dépens", r"kosten|parteientsch|dépens|frais|unentgeltlich|assistance judiciaire"),
]
FR = {de: fr for de, fr, _ in VOCAB}
_COMPILED = [(de, re.compile(p, re.I)) for de, _, p in VOCAB]


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
