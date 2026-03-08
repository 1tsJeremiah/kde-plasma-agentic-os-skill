# Best Practices

## Design Principles

- Keep desktop automation explicit and auditable.
- Prefer official KDE/freedesktop DBus interfaces over UI click simulation.
- Use read-before-write and verify-after-write for all mutating calls.

## Endpoint Design

- Keep the server local-only (`127.0.0.1`/`::1`).
- Keep endpoint methods allowlisted and typed.
- Reject path traversal and shell injection opportunities.
- Require auth tokens unless in explicit isolated debug mode.

## KWin-Specific Guidance

- Use `/VirtualDesktopManager` for desktop lifecycle and `/KWin` for active desktop switching.
- Use `/Scripting` for plugin lifecycle rather than direct file edits in KWin internals.
- Use effect endpoints for temporary visual workflows; avoid permanent state mutation when not needed.

## Operational Hygiene

- Store token in `~/.config/mindstack/kde-agent-endpoint.env` with mode `600`.
- Use `systemctl --user` for lifecycle management.
- Keep changes reversible and document endpoint additions in PRs.
