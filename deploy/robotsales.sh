#!/usr/bin/env bash
# Deploy the Lex Aperta API to the team server (SSH alias "robotsales", Miguel's Mac Mini).
# Public URL: https://api.robotross.art/lex/   (Caddy: handle_path /lex/* -> 127.0.0.1:8794)
#
#   deploy/robotsales.sh              pull latest main on the server and restart
#   deploy/robotsales.sh --db FILE    also replace the server database with FILE (atomic swap)
#
# Secrets live only on the server in /opt/lex-aperta/.env (0600, user lex): LLM_*, LEX_EDITOR_KEYS
# (SHA-256 hashes), LEX_CORS_ORIGINS. Nothing secret is in this script or the repo.
# data/stats.json (/stats page) and site/api/ travel via git: commit them, then deploy.
set -euo pipefail
HOST=robotsales
DEST=/opt/lex-aperta

if [ "${1:-}" = "--db" ]; then
  DB="${2:?usage: --db FILE}"
  # Refuse missing/empty DBs: sqlite3 would silently create an empty file and we'd deploy no data.
  [ -s "$DB" ] || { echo "refuse: $DB missing or empty" >&2; exit 1; }
  N=$(sqlite3 "$DB" "SELECT COUNT(*) FROM judgements;" 2>/dev/null || echo 0)
  [ "$N" -gt 0 ] || { echo "refuse: $DB has no judgements" >&2; exit 1; }
  # Consistent snapshot (includes WAL content) instead of copying a live file
  SNAP=$(mktemp -t lexdb).sqlite
  sqlite3 "$DB" ".backup '$SNAP'"
  echo "uploading $N judgements from $DB"
  rsync -az "$SNAP" "$HOST:$DEST/data/suva.sqlite.new"
  rm -f "$SNAP"
fi

ssh "$HOST" "set -e; cd $DEST
  sudo -u lex git pull -q --ff-only origin main
  sudo -u lex venv/bin/pip -q install -r requirements.txt
  if [ -f data/suva.sqlite.new ]; then chown lex:lex data/suva.sqlite.new; mv data/suva.sqlite.new data/suva.sqlite; fi
  systemctl restart lex-aperta; sleep 3; systemctl is-active lex-aperta
  echo deployed: \$(sudo -u lex git log --oneline -1)"
curl -s -o /dev/null -w "public /api/status: %{http_code}\n" https://api.robotross.art/lex/api/status
