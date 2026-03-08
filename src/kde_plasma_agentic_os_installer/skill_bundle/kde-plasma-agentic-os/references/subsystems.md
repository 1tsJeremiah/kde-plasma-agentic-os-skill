# KDE Plasma Subsystem Map

Use this map to pick the most stable control surface for a task.

## 1. Shell and Panels

- D-Bus service: `org.kde.plasmashell`
- Object path: `/PlasmaShell`
- Interface: `org.kde.PlasmaShell`
- Useful methods:
  - `toggleDashboard()`
  - `toggleActivityManager()`
  - `toggleWidgetExplorer()`
  - `activateLauncherMenu()`
  - `evaluateScript(script)`

Example:

```bash
qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.toggleDashboard
```

## 2. Windows and Desktops (KWin)

- D-Bus service: `org.kde.KWin`
- Object path: `/KWin`
- Interface: `org.kde.KWin`
- Useful methods:
  - `currentDesktop()`
  - `setCurrentDesktop(int)`
  - `nextDesktop()`
  - `previousDesktop()`
  - `queryWindowInfo()`
  - `supportInformation()`

Examples:

```bash
qdbus6 org.kde.KWin /KWin org.kde.KWin.currentDesktop
qdbus6 org.kde.KWin /KWin org.kde.KWin.setCurrentDesktop 2
```

## 3. App Search and Launch (KRunner)

- D-Bus service: `org.kde.krunner`
- Object path: `/App`
- Interface: `org.kde.krunner.App`
- Useful methods:
  - `display()`
  - `toggleDisplay()`
  - `query(term)`

Example:

```bash
qdbus6 org.kde.krunner /App org.kde.krunner.App.query "System Settings"
```

## 4. Notifications

- D-Bus service: `org.freedesktop.Notifications`
- Object path: `/org/freedesktop/Notifications`
- Interface: `org.freedesktop.Notifications`
- Useful methods:
  - `Notify(...)`
  - `CloseNotification(id)`
  - `GetCapabilities()`

Example:

```bash
gdbus call --session \
  --dest org.freedesktop.Notifications \
  --object-path /org/freedesktop/Notifications \
  --method org.freedesktop.Notifications.Notify \
  "codex" 0 "" "Codex" "Task complete" [] {} 3000
```

## 5. Displays and Layout

- CLI tool: `kscreen-doctor`
- Use `-j` to inspect JSON configuration.
- Apply multiple changes atomically by passing settings in one invocation.

Examples:

```bash
kscreen-doctor -j
kscreen-doctor output.HDMI-2.enable output.HDMI-2.mode.1920x1080@60
```

## 6. Persistent KDE Settings (KConfig)

- Read with `kreadconfig6`
- Write with `kwriteconfig6`
- Use `--notify` on writes when immediate change propagation is needed.

Examples:

```bash
kreadconfig6 --file plasmarc --group Theme --key name --default BreezeDark
kwriteconfig6 --file plasmarc --group Theme --key name Breeze
```

## 7. Power and Battery

- D-Bus service: `org.kde.Solid.PowerManagement`
- Object path: `/org/kde/Solid/PowerManagement`
- Interface: `org.kde.Solid.PowerManagement`
- Useful methods:
  - `currentProfile()`
  - `batteryRemainingTime()`
  - `isLidClosed()`
  - `isActionSupported(action)`

## 8. Portals and Sandboxed Integrations

- D-Bus service: `org.freedesktop.portal.Desktop`
- Object path: `/org/freedesktop/portal/desktop`
- Use portal interfaces for screenshot, notification, network status, and background permission flows.

## 9. Supporting Linux Controls

- Network: `nmcli`
- Audio: `pactl`
- User services: `systemctl --user`
- Session and login: `loginctl`

Use these when KDE-specific interfaces are unavailable or incomplete.
