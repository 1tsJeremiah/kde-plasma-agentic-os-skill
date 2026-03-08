# KDE Plasma Agentic OS Skill

A public, distributable Codex skill for KDE Plasma automation on Linux.

This project ships one consolidated skill (`kde-plasma-agentic-os`) plus a local-only endpoint stack that exposes safe, allowlisted desktop operations for agents.

## What It Does

- Automates KDE Plasma components through official interfaces:
  - `org.kde.plasmashell`
  - `org.kde.KWin` and KWin sub-interfaces
  - `org.kde.krunner`
  - `org.freedesktop.Notifications`
  - `org.freedesktop.portal.Desktop`
- Manages display state with `kscreen-doctor`.
- Reads/writes persistent KDE settings with `kreadconfig6` and `kwriteconfig6`.
- Runs a token-protected local API (`127.0.0.1`) for repeatable agent workflows.
- Includes helper scripts for KWin desktop, script, and effects lifecycle.

## Security Model (Best Practices)

- Bind only to loopback (`127.0.0.1`/`::1`).
- Require bearer token authentication by default.
- Use allowlisted endpoints only (no generic shell-exec endpoint).
- Keep token in a private env file (`chmod 600`).
- Never expose the endpoint over public ingress or tunnel.

## Quick Install

### Option A: pipx from PyPI (after first publish)

```bash
pipx install kde-plasma-agentic-os-skill
kde-plasma-skill install --with-service
```

### Option B: pip from PyPI (after first publish)

```bash
python3 -m pip install kde-plasma-agentic-os-skill
kde-plasma-skill install --with-service
```

### Option C: pipx from GitHub (immediate fallback)

```bash
pipx install git+https://github.com/1tsJeremiah/kde-plasma-agentic-os-skill.git@main
kde-plasma-skill install --with-service
```

### Option D: from source

```bash
git clone https://github.com/1tsJeremiah/kde-plasma-agentic-os-skill.git
cd kde-plasma-agentic-os-skill
python3 -m pip install .
kde-plasma-skill install --with-service
```

## CLI Commands

```bash
kde-plasma-skill install [--dest ~/.codex/skills] [--force] [--with-service]
kde-plasma-skill service-install [--skill-path ~/.codex/skills/kde-plasma-agentic-os]
kde-plasma-skill service-uninstall [--skill-path ~/.codex/skills/kde-plasma-agentic-os]
kde-plasma-skill doctor [--json]
```

## Service and Endpoint

After `--with-service`, the user service runs:

- Unit: `~/.config/systemd/user/kde-agent-endpoint.service`
- Token env file: `~/.config/mindstack/kde-agent-endpoint.env`

Check status:

```bash
systemctl --user status kde-agent-endpoint.service
journalctl --user -u kde-agent-endpoint.service -f
```

## Example Endpoint Calls

```bash
source ~/.config/mindstack/kde-agent-endpoint.env
python3 ~/.codex/skills/kde-plasma-agentic-os/scripts/kde_agentctl.py GET /health --token "$KDE_AGENT_TOKEN" --base-url "http://${KDE_AGENT_HOST}:${KDE_AGENT_PORT}"
python3 ~/.codex/skills/kde-plasma-agentic-os/scripts/kde_agentctl.py GET /kwin/desktops --token "$KDE_AGENT_TOKEN" --base-url "http://${KDE_AGENT_HOST}:${KDE_AGENT_PORT}"
python3 ~/.codex/skills/kde-plasma-agentic-os/scripts/kde_agentctl.py POST /kwin/desktop/switch --token "$KDE_AGENT_TOKEN" --base-url "http://${KDE_AGENT_HOST}:${KDE_AGENT_PORT}" --json '{"desktop":2}'
```

## Project Layout

```text
src/kde_plasma_agentic_os_installer/
  cli.py
  skill_bundle/kde-plasma-agentic-os/
    SKILL.md
    agents/openai.yaml
    scripts/
    references/
```

## Compatibility

- KDE Plasma 6+ (tested on Plasma 6.6.1)
- Linux with user session DBus
- Python 3.10+

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

Best-practice architecture guidance is in [docs/BEST_PRACTICES.md](docs/BEST_PRACTICES.md).
Publishing setup is in [docs/PUBLISHING.md](docs/PUBLISHING.md).

## License

MIT, see [LICENSE](LICENSE).
