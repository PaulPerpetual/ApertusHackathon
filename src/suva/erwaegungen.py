"""Split a Federal Court ruling into its numbered considerations (Erwägungen / considérants / considerandi).

The text (as loaded from entscheidsuche.ch) has a marker ("Erwägungen:", "Considérant en droit :",
"Considerando in diritto:") followed by numbered paragraphs, each number on its own line ("2.", "5.2.1."),
and ends with the operative part ("Demnach erkennt das Bundesgericht", "Par ces motifs", "Per questi motivi").

parse(text) -> [{"nr": "5.2.1", "start": <char offset>, "end": <char offset>, "preview": "<first words>"}]
Offsets index into the same text string the API returns, so the UI can jump to a consideration.
"""
import re

START = re.compile(r"(Erwägungen?|Erwägung|Considérant en droit|Considérants?|Considerando in diritto|Considerandi)\s*:?\s*\n")
END = re.compile(r"\n\s*(Demnach erkennt|Par ces motifs|Per questi motivi)")
NUM = re.compile(r"^[ \t]*(\d{1,2}(?:\.\d{1,2}){0,4})(?:\.?[ \t]*$|\.[ \t]+(?=\S))", re.M)  # "5.2." alone on its line, or "5.2. Text" at line start
REF = re.compile(r"\((?:E\.|Erw\.|Erwägung|consid\.|cons\.)\s*([0-9][0-9.]*(?:\s*(?:und|et|e|,|-|–)\s*[0-9][0-9.]*)*)\)")


def parse(text):
    if not text:
        return []
    m = START.search(text)
    begin = m.end() - 1 if m else 0
    e = END.search(text, begin)
    stop = e.start() if e else len(text)
    hits = [(mm.group(1).rstrip("."), mm.start()) for mm in NUM.finditer(text, begin, stop)]
    out = []
    for i, (nr, pos) in enumerate(hits):
        end = hits[i + 1][1] if i + 1 < len(hits) else stop
        body = re.sub(r"\s+", " ", text[pos:end]).strip()
        body = re.sub(r"^" + re.escape(nr) + r"\.?\s*", "", body)
        out.append({"nr": nr, "start": pos, "end": end, "preview": body[:90]})
    return out


def numbers(text):
    return [c["nr"] for c in parse(text)]


def outline(text, max_chars=160):
    """Compact list for prompts: 'E. 5.2: <first words>'."""
    return "\n".join(f"E. {c['nr']}: {c['preview'][:max_chars]}" for c in parse(text))


def check_refs(summary, valid):
    """Return (refs found, refs not in the ruling) for '(E. 5.2)' / '(consid. 5.2 et 5.3)' style references."""
    found, bad = [], []
    valid = set(valid)
    for grp in REF.findall(summary or ""):
        for nr in re.findall(r"\d{1,2}(?:\.\d{1,2}){0,4}", grp):
            found.append(nr)
            if nr not in valid:
                bad.append(nr)
    return found, bad


def dispositiv(text, max_chars=900):
    """The operative part ("Demnach erkennt das Bundesgericht: 1. Die Beschwerde wird ...") verbatim."""
    e = END.search(text or "")
    return re.sub(r"\s+", " ", text[e.start():e.start() + max_chars]).strip() if e else ""


_OUT = {
    "admitted": r"(?:wird|werden)\s+(?:teilweise\s+)?gutgeheissen|est\s+(?:partiellement\s+)?admis|(?:è|sono)\s+(?:parzialmente\s+)?accolt",
    "rejected": r"(?:wird|werden)\s+abgewiesen|est\s+rejeté|(?:è|sono)\s+respint",
    "inadmissible": r"nicht\s+eingetreten|irrecevable|inammissibil",
}
_SUM = {
    "admitted": r"hiess\s+(?:die\s+)?(?:Beschwerde\s+)?(?:teilweise\s+)?gut|(?:wird|wurde)\s+(?:teilweise\s+)?gutgeheissen|a\s+(?:partiellement\s+)?admis|admet\s+(?:partiellement\s+)?le\s+recours|est\s+(?:partiellement\s+)?admis",
    "rejected": r"wies\s+(?:die\s+)?Beschwerde\s+ab|(?:wird|wurde)\s+abgewiesen|a\s+rejeté|rejette\s+le\s+recours|est\s+rejeté",
}


def outcome(text):
    """Federal Court outcome from the Dispositiv: 'admitted' | 'rejected' | 'inadmissible' | None (first item)."""
    d = dispositiv(text, 500)
    first = re.split(r"\b2\.\s", d, maxsplit=1)[0]
    for k, pat in _OUT.items():
        if re.search(pat, first, re.I):
            return k
    return None


def outcome_conflict(summary, text):
    """A sentence in the summary that states the opposite outcome for the Federal Court, or None.
    Sentences about the cantonal court / lower instance are ignored."""
    real = outcome(text)
    if real not in ("admitted", "rejected"):
        return None
    wrong = "rejected" if real == "admitted" else "admitted"
    lower = re.compile(r"kantonal|Vorinstanz|Versicherungsgericht|Verwaltungsgericht|tribunal cantonal|cour cantonale|"
                       r"autorité précédente|premiers juges|juges cantonaux|instance précédente|IV-Stelle|office AI", re.I)
    for sent in re.split(r"(?<=[.!?])\s+", summary or ""):
        m = re.search(_SUM[wrong], sent, re.I)
        if not m or not re.search(r"Beschwerde|recours", sent, re.I):
            continue
        if re.search(r"surplus|im Übrigen|im übrigen|teilweise|partiellement|\d[A-Z]_\d+/\d{4}", sent, re.I):
            continue  # partial outcome or another ruling cited
        if lower.search(sent[:m.start()]) and not re.search(r"Bundesgericht|BGer|Tribunal fédéral|\bTF\b", sent[:m.start()]):
            continue  # the sentence reports the lower instance's decision
        return sent.strip()
    return None
