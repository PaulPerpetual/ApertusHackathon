# Lex Aperta: results (Hack Apertus Zürich 2026, Challenge Suva)

Team: Paul · Miguel Rodriguez. All selections, rankings and texts by Apertus v1.5 70B (swiss-ai, via CSCS/Keera).

| File | Content |
| --- | --- |
| `hitlist_Q2_2026.csv` | **Hit list Apr–Jun 2026**: `UrteilID, Rang, Kategorie` (normal / Grenzfall). 163 rulings = 77 normal + 86 Grenzfälle; Grenzfälle rank below normal. |
| `hitlist_Q2_2026_detail.csv` | Same list plus score, decision date and German title |
| `hitlist_Q2_2026.txt` | Same list, comma-separated (style `8C_691/2024, 9C_612/2025`) |
| `top5_2026-06.pdf` | **Top 5 June 2026** (by decision date): full summaries in German and French |
| `top10_2026-06_overview.pdf` | Top 10 June 2026: titles DE/FR and the reason for relevance, with the rank on the overall list |

Rebuild from the live app (includes lawyer edits): `python src/build_results.py`.
Live app: <https://api.robotross.art/lex/>. Edits made by the team during review are visible in each ruling's history.
