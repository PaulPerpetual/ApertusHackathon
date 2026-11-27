"""Copy human decisions from the server DB into the master DB before a DB deploy, so they are never overwritten.

Human fields (never written by the pipeline):
  judgements.status/status_by/status_at (Erledigt, Nicht relevant)
  assessments.score_override/override_by/override_at, explanation_*_human, explanation_edited_by/at, tags_human
  summaries text/edited_by/edited_at where a person edited it
  edits (history) and notes: rows missing locally are appended

    python src/merge_server_edits.py SERVER_COPY.sqlite MASTER.sqlite
"""
import sqlite3
import sys

J_FIELDS = ("status", "status_by", "status_at")
A_FIELDS = ("score_override", "override_by", "override_at", "explanation_de_human", "explanation_fr_human",
            "explanation_edited_by", "explanation_edited_at", "tags_human")


def cols(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


def main(server, master):
    src = sqlite3.connect(server)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(master, timeout=30)
    n = {"status": 0, "assessment": 0, "summary": 0, "edits": 0, "notes": 0}
    jf = [f for f in J_FIELDS if f in cols(src, "judgements") and f in cols(dst, "judgements")]
    for r in src.execute(f"SELECT slug, {', '.join(jf)} FROM judgements WHERE status IS NOT NULL AND status != 'new'"):
        n["status"] += dst.execute(f"UPDATE judgements SET {', '.join(f + '=?' for f in jf)} WHERE slug=?",
                                   (*[r[f] for f in jf], r["slug"])).rowcount
    af = [f for f in A_FIELDS if f in cols(src, "assessments") and f in cols(dst, "assessments")]
    cond = " OR ".join(f"{f} IS NOT NULL" for f in af)
    for r in src.execute(f"SELECT slug, {', '.join(af)} FROM assessments WHERE {cond}"):
        n["assessment"] += dst.execute(f"UPDATE assessments SET {', '.join(f + '=?' for f in af)} WHERE slug=?",
                                       (*[r[f] for f in af], r["slug"])).rowcount
    for r in src.execute("SELECT slug, lang, text, edited_by, edited_at FROM summaries WHERE edited_by IS NOT NULL"):
        n["summary"] += dst.execute("UPDATE summaries SET text=?, edited_by=?, edited_at=? WHERE slug=? AND lang=?",
                                    (r["text"], r["edited_by"], r["edited_at"], r["slug"], r["lang"])).rowcount
    have = {(r[0], r[1], r[2], r[3]) for r in dst.execute("SELECT slug, field, editor, at FROM edits")}
    for r in src.execute("SELECT slug, field, old_value, new_value, editor, at FROM edits"):
        if (r["slug"], r["field"], r["editor"], r["at"]) not in have:
            dst.execute("INSERT INTO edits (slug, field, old_value, new_value, editor, at) VALUES (?,?,?,?,?,?)", tuple(r))
            n["edits"] += 1
    if "notes" in {t[0] for t in src.execute("SELECT name FROM sqlite_master")}:
        dst.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT, text TEXT, editor TEXT, at TEXT)")
        have = {(r[0], r[1], r[2]) for r in dst.execute("SELECT slug, editor, at FROM notes")}
        for r in src.execute("SELECT slug, text, editor, at FROM notes"):
            if (r["slug"], r["editor"], r["at"]) not in have:
                dst.execute("INSERT INTO notes (slug, text, editor, at) VALUES (?,?,?,?)", tuple(r))
                n["notes"] += 1
    dst.commit()
    print("merged from server:", n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
