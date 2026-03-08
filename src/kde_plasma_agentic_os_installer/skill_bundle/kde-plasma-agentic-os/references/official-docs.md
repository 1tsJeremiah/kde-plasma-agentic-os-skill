# Official Documentation Sources

Use these sources first when designing or extending KDE Plasma automation flows.

## KDE Plasma and KWin

- Plasma scripting overview: https://develop.kde.org/docs/plasma/scripting/
  - Shows `org.kde.PlasmaShell.evaluateScript` usage and `plasma-interactiveconsole` workflow.
- Plasma shell API examples: https://develop.kde.org/docs/plasma/scripting/api/
- KWin documentation index: https://develop.kde.org/docs/plasma/kwin/
- KWin scripting API reference: https://develop.kde.org/docs/plasma/kwin/api/

## Freedesktop Specifications

- Desktop Notifications spec (`org.freedesktop.Notifications`):
  - https://specifications.freedesktop.org/notification-spec/latest/
- XDG Desktop Portal docs and interface index:
  - https://flatpak.github.io/xdg-desktop-portal/docs/

## Qt and D-Bus

- Qt D-Bus module overview:
  - https://doc.qt.io/qt-6/qtdbus-index.html

## systemd User Services (for local endpoint lifecycle)

- `systemd.service`:
  - https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- `systemd.socket`:
  - https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html
- `systemctl`:
  - https://www.freedesktop.org/software/systemd/man/latest/systemctl.html

## Local Command Help (host-specific)

Use these local command references to match runtime behavior on the current machine:

- `qdbus6 --help`
- `kscreen-doctor --help`
- `kreadconfig6 --help`
- `kwriteconfig6 --help`
- `gdbus help`
- `busctl --help`
