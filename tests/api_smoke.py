"""End-to-end smoke test of the hosted Lex Aperta API (or any base URL).

Checks every endpoint the UI uses, the security rules (keys, CORS) and data sanity.
Writes are no-ops or reverted, except --add, which runs a real on-demand Apertus job.

    python tests/api_smoke.py [--base https://api.robotross.art/lex] [--key $MIGUEL_KEY] [--add 8C_580/2025]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

PAGES_ORIGIN = "https://paulperpetual.github.io"
results = []


def req(base, path, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(base + path, data=data, method=method, headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read()
            return resp.status, raw, dict(resp.headers), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers), time.time() - t0


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://api.robotross.art/lex")
    ap.add_argument("--key", default="", help="editor key for write tests")
    ap.add_argument("--add", default="", help="docket for a real POST /api/judgements job (uses Apertus)")
    a = ap.parse_args()
    b = a.base.rstrip("/")

    # --- pages
    for p in ("/", "/debug", "/stats", "/static/app.js"):
        s, raw, _, t = req(b, p)
        check(f"GET {p}", s == 200, f"{s}, {len(raw)} B, {t:.2f}s")

    # --- status
    s, raw, _, _ = req(b, "/api/status")
    st = json.loads(raw) if s == 200 else {}
    check("GET /api/status", s == 200, json.dumps(st)[:120])
    check("status: real model (not mock)", st.get("mock") is False and "apertus" in str(st.get("model")))
    check("status: editor key required", st.get("editor_key_required") is True)
    check("status: data_version for auto-refresh", bool(st.get("data_version")))

    # --- list
    s, raw, _, t = req(b, "/api/judgements")
    cards = json.loads(raw) if s == 200 else []
    check("GET /api/judgements", s == 200 and len(cards) > 0, f"{len(cards)} cards, {len(raw)//1024} KB, {t:.2f}s")
    scored = [c for c in cards if str(c.get("model", "")).startswith("apertus")]
    hit = [c for c in scored if (c.get("score") or 0) >= 60]  # hit list = Apertus score >= 60 (finalize.py)
    check("cards scored by Apertus", len(scored) >= 150, f"{len(scored)}")
    check("hit list (score >= 60)", len(hit) >= 60, f"{len(hit)}")
    tags = [t for c in scored for t in (c.get("tags") or [])]
    check("tags without '#' (UI adds it)", not any(str(t).startswith("#") for t in tags), f"{len(set(tags))} distinct")
    check("no duplicate tags on a card", all(len(c.get("tags") or []) == len(set(c.get("tags") or [])) for c in scored))
    check("FR tags aligned with DE", all(len(c.get("tags_fr") or []) in (0, len(c.get("tags") or [])) for c in scored))
    check("cards sorted by score", all((cards[i].get("score") or 0) >= (cards[i + 1].get("score") or 0)
                                       for i in range(min(len(cards), 300) - 1)))
    need = {"slug", "docket", "decision_date", "score", "title_de", "title_fr", "explanation_de", "tags"}
    check("card fields present", need <= set(cards[0]) if cards else False, ", ".join(sorted(need - set(cards[0] if cards else {}))))
    summ = [c for c in hit if c.get("has_summary") or c.get("n_summaries")]
    check("hit-list rulings with summaries", True, f"{len(summ)} of {len(hit)} so far")

    # --- detail
    top = hit[0] if hit else (cards[0] if cards else None)
    if top:
        s, raw, _, t = req(b, f"/api/judgements/{top['slug']}")
        d = json.loads(raw) if s == 200 else {}
        check(f"GET /api/judgements/{top['slug']}", s == 200, f"{len(raw)//1024} KB, {t:.2f}s")
        check("detail has full text", len(d.get("text") or "") > 2000, f"{len(d.get('text') or '')} chars")
        withsum = next((c for c in hit if c.get("has_summary") or c.get("n_summaries")), None)
        if withsum:
            s, raw, _, _ = req(b, f"/api/judgements/{withsum['slug']}")
            d2 = json.loads(raw)
            sm = d2.get("summaries") or {}
            check("detail has DE + FR summaries", bool(sm.get("de")) and bool(sm.get("fr")), withsum["docket"])
    s, _, _, _ = req(b, "/api/judgements/0X_0_0000")
    check("unknown slug -> 404", s == 404, str(s))

    # --- knowledge base
    s, raw, _, t = req(b, "/api/kb?q=Kausalzusammenhang")
    kb = json.loads(raw) if s == 200 else None
    n = len(kb) if isinstance(kb, list) else len((kb or {}).get("results", kb or []))
    check("GET /api/kb?q=Kausalzusammenhang", s == 200 and n > 0, f"{n} results, {t:.2f}s")
    s, raw, _, _ = req(b, "/api/kb/example/8C_178%2F2025")
    check("GET /api/kb/example/8C_178/2025", s == 200, str(s))

    # --- stats
    s, raw, _, _ = req(b, "/api/stats")
    stx = json.loads(raw) if s == 200 else {}
    check("GET /api/stats", s == 200 and "window" in stx and "aprjun" in stx)

    # --- security
    slug = top["slug"] if top else "x"
    s, _, _, _ = req(b, f"/api/judgements/{slug}/score", "DELETE", {"editor": "smoke"})
    check("write without key -> 401", s == 401, str(s))
    s, _, _, _ = req(b, f"/api/judgements/{slug}/score", "DELETE", {"editor": "smoke"}, {"X-Lex-Key": "wrong"})
    check("write with wrong key -> 401", s == 401, str(s))
    s, _, h, _ = req(b, "/api/judgements", "OPTIONS", headers={"Origin": PAGES_ORIGIN,
                     "Access-Control-Request-Method": "PUT", "Access-Control-Request-Headers": "x-lex-key,content-type"})
    acao = {k.lower(): v for k, v in h.items()}.get("access-control-allow-origin")
    check("CORS preflight from GitHub Pages", s == 200 and acao == PAGES_ORIGIN, f"{s} {acao}")
    s, _, h, _ = req(b, "/api/judgements", "OPTIONS", headers={"Origin": "https://evil.example",
                     "Access-Control-Request-Method": "POST"})
    acao = {k.lower(): v for k, v in h.items()}.get("access-control-allow-origin")
    check("CORS refused for other origins", acao is None, f"{s} {acao}")
    for p in ("/.env", "/static/../../.env", "/data/suva.sqlite"):
        s, _, _, _ = req(b, p)
        check(f"GET {p} not exposed", s in (400, 404), str(s))

    if a.key:
        # score override then revert: net no change, both logged under the key's owner
        noov = next((c for c in cards if c.get("score_override") is None and c.get("score") is not None), None)
        if noov:
            orig = noov["score"]
            s1, _, _, _ = req(b, f"/api/judgements/{noov['slug']}/score", "PUT", {"score": 55, "editor": "smoke"},
                              {"X-Lex-Key": a.key})
            s2, raw, _, _ = req(b, f"/api/judgements/{noov['slug']}")
            now = json.loads(raw).get("score") if s2 == 200 else None
            s3, _, _, _ = req(b, f"/api/judgements/{noov['slug']}/score", "DELETE", {"editor": "smoke"},
                              {"X-Lex-Key": a.key})
            s4, raw, _, _ = req(b, "/api/judgements")
            back = next((c for c in json.loads(raw) if c["slug"] == noov["slug"]), {})
            check("write with key: override + revert", s1 == 200 and s3 == 200 and back.get("score") == orig,
                  f"{noov['docket']}: {orig} -> override -> {back.get('score')}")
        s, _, _, _ = req(b, "/api/judgements", "POST", {"docket": "rm -rf /"}, {"X-Lex-Key": a.key})
        check("POST bad docket -> 400", s == 400, str(s))
        if a.add:
            s, raw, _, _ = req(b, "/api/judgements", "POST", {"docket": a.add}, {"X-Lex-Key": a.key})
            check(f"POST /api/judgements {a.add} (job started)", s == 200, raw.decode()[:100])
            t0 = time.time()
            while time.time() - t0 < 600:
                time.sleep(10)
                st = json.loads(req(b, "/api/status")[1])
                job = (st.get("jobs") or {}).get(a.add, {})
                if job.get("status") in ("done", "error"):
                    break
            check(f"on-demand Apertus job for {a.add}", job.get("status") == "done",
                  f"{job} after {time.time() - t0:.0f}s")

    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} passed" + (f"; FAILED: {bad}" if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
