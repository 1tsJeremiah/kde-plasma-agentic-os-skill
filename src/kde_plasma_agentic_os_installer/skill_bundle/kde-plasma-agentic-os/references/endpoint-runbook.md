# Local Endpoint Runbook

Use this runbook to expose KDE actions as local machine endpoints for agent workflows.

## Safety Rules

- Bind only to loopback (`127.0.0.1` or `::1`).
- Require a bearer token by default.
- Avoid exposing raw shell execution endpoints.
- Keep endpoints scoped to allowed operations.
- Do not expose this endpoint through a public listener.

## Start the Endpoint Server

```bash
export KDE_AGENT_TOKEN="change-this-token"
python3 scripts/kde_agent_endpoint.py --host 127.0.0.1 --port 8765
```

For managed startup on login, prefer the installer:

```bash
bash scripts/install_user_service.sh
```

## Call Endpoints

Use the helper client:

```bash
python3 scripts/kde_agentctl.py GET /health --token "$KDE_AGENT_TOKEN"
python3 scripts/kde_agentctl.py GET /capabilities --token "$KDE_AGENT_TOKEN"
python3 scripts/kde_agentctl.py GET /kwin/desktops --token "$KDE_AGENT_TOKEN"
python3 scripts/kde_agentctl.py POST /kwin/desktop/switch --token "$KDE_AGENT_TOKEN" --json '{"desktop":2}'
python3 scripts/kde_agentctl.py POST /kwin/script/is-loaded --token "$KDE_AGENT_TOKEN" --json '{"plugin_name":"my-plugin"}'
python3 scripts/kde_agentctl.py POST /notifications/notify --token "$KDE_AGENT_TOKEN" --json '{"summary":"Codex","body":"Task complete"}'
```

## Available Endpoints

- `GET /health`
- `GET /capabilities`
- `GET /kwin/desktops`
- `GET /kwin/objects`
- `GET /kwin/current-desktop`
- `POST /kwin/set-desktop`
- `POST /kwin/desktop/switch`
- `POST /kwin/desktop/create`
- `POST /kwin/desktop/rename`
- `POST /kwin/desktop/remove`
- `POST /kwin/script/start`
- `POST /kwin/script/is-loaded`
- `POST /kwin/script/load`
- `POST /kwin/script/unload`
- `POST /kwin/effect/windowview`
- `POST /kwin/effect/highlight`
- `POST /kwin/nightlight/preview`
- `POST /kwin/nightlight/stop`
- `POST /kwin/nightlight/inhibit`
- `POST /kwin/nightlight/uninhibit`
- `POST /krunner/query`
- `POST /plasmashell/toggle-dashboard`
- `POST /notifications/notify`
- `GET /screen/outputs`
- `POST /screen/apply`
- `GET /config/read`
- `POST /config/write`

## Optional systemd --user Service

Create `~/.config/systemd/user/kde-agent-endpoint.service`:

```ini
[Unit]
Description=KDE Agent Endpoint (local-only)
After=graphical-session.target

[Service]
Type=simple
EnvironmentFile=%h/.config/mindstack/kde-agent-endpoint.env
WorkingDirectory=%h/.codex/skills/kde-plasma-agentic-os
ExecStart=/usr/bin/python3 %h/.codex/skills/kde-plasma-agentic-os/scripts/kde_agent_endpoint.py --host ${KDE_AGENT_HOST} --port ${KDE_AGENT_PORT}
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

Then enable/start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now kde-agent-endpoint.service
systemctl --user status kde-agent-endpoint.service
```

Use `journalctl --user -u kde-agent-endpoint.service -f` for logs.

To remove the unit while keeping the token file:

```bash
bash scripts/uninstall_user_service.sh
```
