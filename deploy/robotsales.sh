#!/usr/bin/env bash
# Deploy the Lex Aperta API to the team server (SSH alias "robotsales", Miguel's Mac Mini).
# Public URL: https://api.robotross.art/lex/   (Caddy: handle_path /lex/* -> 127.0.0.1:8794)
#
#   deploy/robotsales.sh              pull latest main on the server and restart
#   deploy/robotsales.sh --db FILE    also replace the server database with FILE (atomic swap)
#
# Secrets live only on the server in /opt/lex-aperta/.env (0600, user lex): LLM_*, LEX_EDITOR_KEYS
# (SHA-256 hashes), LEX_CORS_ORIGINS. Nothing secret is in this script or the repo.
set -euo pipefail
HOST=robotsales
DEST=/opt/lex-aperta

if [ "${1:-}" = "--db" ]; then
  DB="${2:?usage: --db FILE}"
  sqlite3 "$DB" "PRAGMA wal_checkpoint(TRUNCATE);" >/dev/null
  rsync -az "$DB" "$HOST:$DEST/data/suva.sqlite.new"
fi

ssh "$HOST" "set -e; cd $DEST
  sudo -u lex git pull -q --ff-only origin main
  sudo -u lex venv/bin/pip -q install -r requirements.txt
  if [ -f data/suva.sqlite.new ]; then chown lex:lex data/suva.sqlite.new; mv data/suva.sqlite.new data/suva.sqlite; fi
  systemctl restart lex-aperta; sleep 3; systemctl is-active lex-aperta
  echo deployed: \$(sudo -u lex git log --oneline -1)"
curl -s -o /dev/null -w "public /api/status: %{http_code}\n" https://api.robotross.art/lex/api/status
