# KWin Automation

Use this reference for KWin-specific operations that go beyond shell-level Plasma controls.

## Key Interfaces

- `/KWin` -> `org.kde.KWin`
  - Desktop switching, window info, support info.
- `/Scripting` -> `org.kde.kwin.Scripting`
  - Script load/start/unload and loaded checks.
- `/VirtualDesktopManager` -> `org.kde.KWin.VirtualDesktopManager`
  - Desktop create/rename/remove plus `count/current/desktops`.
- `/org/kde/KWin/Effect/WindowView1` -> `org.kde.KWin.Effect.WindowView1`
- `/org/kde/KWin/HighlightWindow` -> `org.kde.KWin.HighlightWindow`
- `/org/kde/KWin/NightLight` -> `org.kde.KWin.NightLight`

## Included Helpers

- `scripts/kwin_probe.py`
- `scripts/kwin_desktopctl.py`
- `scripts/kwin_scriptctl.py`
- `scripts/kwin_effectctl.py`

## Endpoint Mapping

KWin endpoints exposed by `scripts/kde_agent_endpoint.py`:

- `GET /kwin/desktops`
- `GET /kwin/objects`
- `POST /kwin/desktop/switch` (and compatibility alias `POST /kwin/set-desktop`)
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
