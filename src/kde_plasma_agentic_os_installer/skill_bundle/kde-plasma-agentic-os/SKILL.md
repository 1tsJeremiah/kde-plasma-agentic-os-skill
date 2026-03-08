---
name: kde-plasma-agentic-os
description: Integrate and automate KDE Plasma on Linux using official KDE/freedesktop D-Bus interfaces, KDE CLI utilities, KWin scripting/effect controls, and local-only endpoint patterns. Use when Codex must inspect or control shell widgets, virtual desktops, windows, KWin scripts/effects, display layouts, notifications, KConfig settings, power behavior, or build a robust local API bridge for agentic desktop workflows.
---

# KDE Plasma Agentic OS

Use this skill to treat KDE Plasma as an automatable local platform while staying within local-machine safety constraints.

## Quick Start

1. Run capability discovery first.

```bash
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kde_probe.py
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kde_probe.py --json
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kwin_probe.py
```

2. Choose the narrowest control surface that satisfies the task.

- Use D-Bus for shell, window manager, launcher, notifications, power.
- Use `kscreen-doctor` for display topology and mode changes.
- Use `kreadconfig6` and `kwriteconfig6` for persistent KDE settings.
- Use `nmcli`, `pactl`, and `systemctl --user` for supporting subsystems.
- Use `scripts/kwin_desktopctl.py`, `scripts/kwin_scriptctl.py`, and `scripts/kwin_effectctl.py` for direct KWin automation.

3. Prefer read-first, then write with explicit intent.

- Read state before changing it.
- Apply minimal changes needed for the task.
- Re-read state after writes to confirm the result.

## Subsystem Selection

Use `references/subsystems.md` when you need specific service names, paths, interfaces, and command examples.

- Shell and widgets: `org.kde.plasmashell` `/PlasmaShell`
- Window manager/workspaces: `org.kde.KWin` `/KWin`
- Launcher/search: `org.kde.krunner` `/App`
- Notifications: `org.freedesktop.Notifications`
- Portals: `org.freedesktop.portal.Desktop`
- Power profiles and battery: `org.kde.Solid.PowerManagement`

## Endpoint Mode (Agentic API Bridge)

Use this mode when the task benefits from repeatable endpoint calls instead of ad-hoc shell commands.

1. Start local endpoint server (loopback only, token auth by default).

```bash
export KDE_AGENT_TOKEN="change-this-token"
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kde_agent_endpoint.py --host 127.0.0.1 --port 8765
```

2. Call endpoints with helper client.

```bash
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kde_agentctl.py GET /health --token "$KDE_AGENT_TOKEN"
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kde_agentctl.py GET /capabilities --token "$KDE_AGENT_TOKEN"
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kde_agentctl.py GET /kwin/desktops --token "$KDE_AGENT_TOKEN"
python3 /home/x/.codex/skills/kde-plasma-agentic-os/scripts/kde_agentctl.py POST /kwin/script/is-loaded --token "$KDE_AGENT_TOKEN" --json '{"plugin_name":"my-plugin"}'
```

3. Use `references/endpoint-runbook.md` for endpoint catalog and optional `systemctl --user` service lifecycle.

## References

Load only the file needed for the current task.

- `references/official-docs.md` for official KDE/freedesktop/Qt/systemd documentation links.
- `references/subsystems.md` for practical mapping of KDE subsystems to commands and interfaces.
- `references/endpoint-runbook.md` for local API bridge operations and lifecycle patterns.
- `references/kwin-automation.md` for KWin-specific scripts, interfaces, and endpoint mapping.

## Execution Rules

- Keep endpoint listeners local-only (`127.0.0.1`/`::1`).
- Keep operations allowlisted; avoid generic command execution endpoints.
- Validate command availability before calling subsystem actions.
- Prefer KDE and freedesktop official interfaces before custom hacks.
- Capture before/after state whenever changing display, power, or desktop settings.
