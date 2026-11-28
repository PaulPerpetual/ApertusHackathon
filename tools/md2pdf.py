import markdown, re, sys
src, out = sys.argv[1], sys.argv[2]
lines = open(src).read().split("\n"); fixed = []; infence = False
for i, l in enumerate(lines):
    if l.startswith("```"): infence = not infence
    if not infence and re.match(r"^(- |\d+\. )", l) and fixed and fixed[-1].strip() and not re.match(r"^(\s*- |\s*\d+\. |\s{2,})", fixed[-1]):
        fixed.append("")
    fixed.append(re.sub(r"^  - ", "    - ", l) if not infence else l)
body = markdown.markdown("\n".join(fixed), extensions=["tables", "fenced_code"])
css = ("body{font-family:Arial,Helvetica,sans-serif;font-size:10.5pt;line-height:1.4;max-width:780px;margin:auto;color:#222}"
       "h1{color:#004b87;font-size:20pt}h2{color:#004b87;border-bottom:1px solid #ccc;margin-top:18px}"
       "table{border-collapse:collapse;font-size:9pt;width:100%}td,th{border:1px solid #bbb;padding:3px 6px;vertical-align:top}"
       "th{background:#e8f0f8}code{font-size:8.5pt;background:#f4f4f4}pre{padding:6px;background:#f4f4f4;font-size:7pt;white-space:pre;overflow:hidden}"
       "pre code{font-size:7pt}@page{size:A4;margin:16mm}")
open(out, "w").write(f"<html><head><meta charset=utf-8><style>{css}</style></head><body>{body}</body></html>")
