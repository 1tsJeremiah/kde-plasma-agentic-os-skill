#!/usr/bin/env bash
set -euo pipefail

UNIT_FILE="${HOME}/.config/systemd/user/kde-agent-endpoint.service"

systemctl --user disable --now kde-agent-endpoint.service >/dev/null 2>&1 || true
rm -f "${UNIT_FILE}"
systemctl --user daemon-reload

echo "Removed service unit: ${UNIT_FILE}"
echo "Token file kept: ${HOME}/.config/mindstack/kde-agent-endpoint.env"
