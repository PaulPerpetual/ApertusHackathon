"""Build the results/ folder for the submission from the LIVE app (so lawyer edits are included).

    python src/build_results.py [--base https://api.robotross.art/lex] [--month 2026-06]

Writes:
  results/hitlist_Q2_2026.csv            UrteilID, Rang, Kategorie (normal / Grenzfall), as Suva asked
  results/hitlist_Q2_2026_detail.csv     same plus score, decision date, DE title
  results/hitlist_Q2_2026.txt            comma-separated list (style 8C_691/2024, 9C_612/2025)
  results/top5_<month>.html/.pdf         full DE + FR summaries of the top 5 of the month (by decision date)
  results/top10_<month>_overview.html/.pdf  top 10 of the month: title, reason, rank
PDFs are printed with headless Chrome (if found).
"""
import argparse
import csv
import html
import json
import os
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TEAM = os.environ.get("LEX_TEAM", "Paul Grünenwald · Miguel Rodriguez")
PROJECT = "Lex Aperta"
MONTHS = {"04": ("April", "avril"), "05": ("Mai", "mai"), "06": ("Juni", "juin")}
CSS = """body{font-family:Arial,Helvetica,sans-serif;font-size:10.5pt;line-height:1.45;color:#222;max-width:760px;margin:auto}
h1{color:#004b87;font-size:18pt;margin-bottom:2px}h2{color:#004b87;font-size:13pt;margin:0 0 4px}
.sub{color:#555;font-size:9.5pt;margin-bottom:14px}.case{border-top:2px solid #004b87;padding-top:10px;margin-top:18px}
.case.break{page-break-before:always;border-top:none}h2,.meta{page-break-after:avoid}.meta{font-size:9pt;color:#555;margin-bottom:8px}.lang{font-weight:bold;color:#004b87;margin-top:10px}
.fr{color:#333}table{border-collapse:collapse;width:100%;font-size:9pt}td,th{border:1px solid #bbb;padding:4px 6px;vertical-align:top;text-align:left}
th{background:#e8f0f8}a{color:#004b87}.band{display:flex;justify-content:space-between;border-bottom:3px solid #004b87;padding-bottom:6px;margin-bottom:12px;font-size:9.5pt;color:#004b87}.band b{font-size:12pt}.foot{margin-top:18px;border-top:1px solid #bbb;padding-top:6px;font-size:8.5pt;color:#666}@page{size:A4;margin:15mm}"""


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=60) as r:
        return json.load(r)


def summary(d, lang):
    s = (d.get("summaries") or {}).get(lang) or {}
    return s.get("text") or s.get("ai_text") or ""


def paras(t):
    return "".join(f"<p>{html.escape(p.strip())}</p>" for p in t.split("\n") if p.strip())


def page(title, body, base):
    band = (f"<div class='band'><span><b>{PROJECT}</b> · Hack Apertus Zürich 2026 · Challenge Suva</span>"
            f"<span>Team: {html.escape(TEAM)}</span></div>")
    foot = (f"<div class='foot'>{PROJECT} · Team {html.escape(TEAM)} · Erstellt mit Apertus v1.5 70B (swiss-ai) · "
            f"App: <a href='{html.escape(base)}/'>{html.escape(base)}/</a> · Code: github.com/PaulPerpetual/ApertusHackathon</div>")
    return f"<html><head><meta charset=utf-8><title>{title}</title><style>{CSS}</style></head><body>{band}{body}{foot}</body></html>"


def pdf(path_html):
    if os.path.exists(CHROME):
        subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={path_html[:-5]}.pdf", path_html], capture_output=True, timeout=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://api.robotross.art/lex")
    ap.add_argument("--month", default="2026-06")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    hl = get(a.base, "/api/hitlist")
    items = hl["items"]
    cat = lambda c: "Grenzfall" if c == "grenzfall" else "normal"
    with open(os.path.join(OUT, "hitlist_Q2_2026.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["UrteilID", "Rang", "Kategorie"])
        for it in items:
            w.writerow([it["docket"], it["rank"], cat(it["category"])])
    with open(os.path.join(OUT, "hitlist_Q2_2026_detail.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["UrteilID", "Rang", "Kategorie", "Score", "Entscheiddatum", "Titel"])
        for it in items:
            w.writerow([it["docket"], it["rank"], cat(it["category"]), it["score"], it["decision_date"], it.get("title_de") or ""])
    open(os.path.join(OUT, "hitlist_Q2_2026.txt"), "w").write(", ".join(it["docket"] for it in items) + "\n")

    month = [it for it in items if (it["decision_date"] or "").startswith(a.month)]
    month.sort(key=lambda it: (it["category"] != "normal", it["rank"]))
    top = month[:10]
    det = {it["slug"]: get(a.base, f"/api/judgements/{it['slug']}") for it in top}
    mde, mfr = MONTHS[a.month[5:7]]
    yr = a.month[:4]

    # top 5: full summaries
    body = [f"<h1>Lex Aperta: Top 5 {mde} {yr}</h1><div class='sub'>Die fünf wichtigsten Urteile mit Entscheiddatum im "
            f"{mde} {yr} (Bundesgericht), nach Relevanz für die Suva geordnet. Zusammenfassungen DE/FR erstellt von "
            f"Apertus v1.5 70B. Les cinq arrêts les plus importants rendus en {mfr} {yr}.</div>"]
    for i, it in enumerate(top[:5], 1):
        d = det[it["slug"]]
        body.append(f"<div class='case{' break' if i > 1 else ''}'><h2>{i}. {html.escape(it['docket'])}: {html.escape(it.get('title_de') or '')}</h2>"
                    f"<div class='meta'>{html.escape(it.get('title_fr') or '')}<br>Entscheid vom {it['decision_date']} · "
                    f"{html.escape(d.get('subject') or '')} · Rang {it['rank']} von {hl['count']} auf der Trefferliste · "
                    f"<a href='{html.escape(d.get('url') or '')}'>Urteil auf bger.ch</a></div>"
                    f"<div class='lang'>Zusammenfassung (DE)</div>{paras(summary(d, 'de'))}"
                    f"<div class='lang'>Résumé (FR)</div><div class='fr'>{paras(summary(d, 'fr'))}</div></div>")
    p = os.path.join(OUT, f"top5_{a.month}.html")
    open(p, "w").write(page(f"{PROJECT}: Top 5 {mde} {yr}", "".join(body), a.base))
    pdf(p)

    # top 10 overview
    rows = []
    for i, it in enumerate(top, 1):
        d = det[it["slug"]]
        why = (d.get("assessment") or {}).get("explanation_de_human") or (d.get("assessment") or {}).get("explanation_de") or ""
        rows.append(f"<tr><td>{i}</td><td><b>{html.escape(it['docket'])}</b><br>{it['decision_date']}<br>Gesamtrang {it['rank']}</td>"
                    f"<td><b>{html.escape(it.get('title_de') or '')}</b><br><span class='fr'>{html.escape(it.get('title_fr') or '')}</span>"
                    f"<br>{html.escape(why)}</td></tr>")
    body = (f"<h1>Lex Aperta: Top 10 {mde} {yr}</h1><div class='sub'>Übersicht der zehn wichtigsten Urteile mit Entscheiddatum im "
            f"{mde} {yr}, mit Titel und Begründung der Relevanz (Apertus v1.5 70B). Die Top 5 haben ausführliche Zusammenfassungen "
            f"(top5_{a.month}.pdf); alle Zusammenfassungen sind in der App: {html.escape(a.base)}/</div>"
            f"<table><tr><th>#</th><th>Urteil</th><th>Titel und Begründung</th></tr>{''.join(rows)}</table>")
    p = os.path.join(OUT, f"top10_{a.month}_overview.html")
    open(p, "w").write(page(f"{PROJECT}: Top 10 {mde} {yr}", body, a.base))
    pdf(p)
    print(f"{len(items)} rulings ({hl['normal']} normal, {hl['grenzfall']} Grenzfall); {mde} top 10:", [it["docket"] for it in top])


if __name__ == "__main__":
    main()
