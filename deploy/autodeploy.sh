#!/usr/bin/env bash
# Runs ON the server (every minute via deploy/systemd/lex-autodeploy.timer): if main moved, pull, install and restart.
# Pull-based on purpose: no SSH key in GitHub and no open port; the server only fetches the public repo.
#   install once (as root on the server). The script runs as root, so it is installed as a root-owned COPY:
#     install -o root -g root -m 0755 deploy/autodeploy.sh /usr/local/sbin/lex-autodeploy
#     cp deploy/systemd/lex-autodeploy.* /etc/systemd/system/ && systemctl daemon-reload
#     systemctl enable --now lex-autodeploy.timer
#   Changes to this file in the repo do NOT take effect until the copy is re-installed (on purpose).
#   logs: journalctl -u lex-autodeploy -n 50
set -euo pipefail
DEST=/opt/lex-aperta
cd "$DEST"
sudo -u lex git fetch -q origin main
LOCAL=$(sudo -u lex git rev-parse HEAD)
REMOTE=$(sudo -u lex git rev-parse origin/main)
[ "$LOCAL" = "$REMOTE" ] && exit 0
echo "updating $LOCAL -> $REMOTE"
sudo -u lex git merge -q --ff-only origin/main
sudo -u lex venv/bin/pip -q install -r requirements.txt
systemctl restart lex-aperta; sleep 3; systemctl is-active lex-aperta
echo "deployed: $(sudo -u lex git log --oneline -1)"
