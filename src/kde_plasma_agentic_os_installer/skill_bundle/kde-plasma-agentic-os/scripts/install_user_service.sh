#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${HOME}/.config/mindstack"
ENV_FILE="${ENV_DIR}/kde-agent-endpoint.env"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_FILE="${UNIT_DIR}/kde-agent-endpoint.service"

mkdir -p "${ENV_DIR}" "${UNIT_DIR}"
chmod 700 "${ENV_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    token="$(openssl rand -hex 32)"
  else
    token="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  fi
  cat > "${ENV_FILE}" <<EOF
KDE_AGENT_TOKEN=${token}
KDE_AGENT_HOST=127.0.0.1
KDE_AGENT_PORT=8765
EOF
fi
chmod 600 "${ENV_FILE}"

cat > "${UNIT_FILE}" <<EOF
[Unit]
Description=KDE Agent Endpoint (local-only)
After=graphical-session.target

[Service]
Type=simple
EnvironmentFile=%h/.config/mindstack/kde-agent-endpoint.env
WorkingDirectory=%h/.codex/skills/kde-plasma-agentic-os
ExecStart=/usr/bin/python3 %h/.codex/skills/kde-plasma-agentic-os/scripts/kde_agent_endpoint.py --host \${KDE_AGENT_HOST} --port \${KDE_AGENT_PORT}
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now kde-agent-endpoint.service
systemctl --user status --no-pager kde-agent-endpoint.service | sed -n '1,40p'

echo "Installed/updated kde-agent-endpoint.service"
echo "Env file: ${ENV_FILE}"
