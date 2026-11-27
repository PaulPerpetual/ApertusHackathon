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
NUM = re.compile(r"^[ \t]*(\d{1,2}(?:\.\d{1,2}){0,4})\.?[ \t]*$", re.M)  # a number alone on its line
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
