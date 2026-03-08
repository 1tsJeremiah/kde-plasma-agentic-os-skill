#!/usr/bin/env python3
"""Local-only HTTP endpoint bridge for KDE Plasma automation."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from kde_probe import collect_probe

MAX_BODY_BYTES = 64 * 1024
ALLOWED_CONFIG_FILE = re.compile(r"^[A-Za-z0-9_.-]+$")
DESKTOP_LITERAL_RE = re.compile(r'\[Argument: \(uss\)\s*(\d+),\s*"([^"]+)",\s*"([^"]*)"\]')


def run_cmd(cmd: List[str], timeout: int = 8) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def run_qdbus(service: str, object_path: str, method: str, *args: str, literal: bool = False) -> Tuple[int, str, str]:
    missing = require_cmd("qdbus6")
    if missing:
        return 127, "", missing

    cmd = ["qdbus6"]
    if literal:
        cmd.append("--literal")
    cmd.extend([service, object_path, method, *args])
    return run_cmd(cmd)


def require_cmd(cmd: str) -> Optional[str]:
    path = shutil.which(cmd)
    if not path:
        return f"Required command not found: {cmd}"
    return None


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        return lowered in {"1", "true", "yes", "on"}
    return bool(value)


def parse_auth_header(header_value: str) -> Optional[str]:
    if not header_value:
        return None
    parts = header_value.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def validate_config_file(file_name: Optional[str]) -> Tuple[bool, Optional[str]]:
    if not file_name:
        return True, None
    if "/" in file_name or ".." in file_name:
        return False, "config file must be a bare filename, not a path"
    if not ALLOWED_CONFIG_FILE.match(file_name):
        return False, "config file contains unsupported characters"
    return True, None


def parse_virtual_desktops_literal(output: str) -> List[Dict[str, Any]]:
    desktops = []
    for order, desktop_id, name in DESKTOP_LITERAL_RE.findall(output):
        desktops.append({"order": int(order), "id": desktop_id, "name": name})
    desktops.sort(key=lambda item: item["order"])
    return desktops


def kwin_desktop_status() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    count_code, count_out, count_err = run_qdbus(
        "org.kde.KWin",
        "/VirtualDesktopManager",
        "org.kde.KWin.VirtualDesktopManager.count",
    )
    if count_code != 0:
        return None, count_err or count_out or f"exit code {count_code}"

    current_num_code, current_num_out, current_num_err = run_qdbus(
        "org.kde.KWin",
        "/KWin",
        "org.kde.KWin.currentDesktop",
    )
    if current_num_code != 0:
        return None, current_num_err or current_num_out or f"exit code {current_num_code}"

    current_id_code, current_id_out, current_id_err = run_qdbus(
        "org.kde.KWin",
        "/VirtualDesktopManager",
        "org.kde.KWin.VirtualDesktopManager.current",
    )
    if current_id_code != 0:
        return None, current_id_err or current_id_out or f"exit code {current_id_code}"

    desktops_code, desktops_out, desktops_err = run_qdbus(
        "org.kde.KWin",
        "/VirtualDesktopManager",
        "org.kde.KWin.VirtualDesktopManager.desktops",
        literal=True,
    )
    if desktops_code != 0:
        return None, desktops_err or desktops_out or f"exit code {desktops_code}"

    try:
        count = int(count_out)
        current_desktop_number = int(current_num_out)
    except ValueError:
        return None, "unexpected KWin desktop numeric response"

    return (
        {
            "count": count,
            "current_desktop_number": current_desktop_number,
            "current_desktop_id": current_id_out,
            "desktops": parse_virtual_desktops_literal(desktops_out),
        },
        None,
    )


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler: BaseHTTPRequestHandler) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    raw_len = handler.headers.get("Content-Length")
    if not raw_len:
        return {}, None

    try:
        size = int(raw_len)
    except ValueError:
        return None, "invalid content-length"

    if size < 0 or size > MAX_BODY_BYTES:
        return None, f"body too large (max {MAX_BODY_BYTES} bytes)"

    raw = handler.rfile.read(size)
    if not raw:
        return {}, None

    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid json: {exc}"

    if not isinstance(payload, dict):
        return None, "json body must be an object"

    return payload, None


def make_handler(expected_token: Optional[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "kde-agent-endpoint/1.0"

        def _authorize(self) -> bool:
            if expected_token is None:
                return True

            token = parse_auth_header(self.headers.get("Authorization", ""))
            if not token:
                token = self.headers.get("X-KDE-Agent-Token")

            return token == expected_token

        def _reject_auth(self) -> None:
            json_response(
                self,
                HTTPStatus.UNAUTHORIZED,
                {
                    "ok": False,
                    "error": "unauthorized",
                    "hint": "Provide Authorization: Bearer <token> or X-KDE-Agent-Token header.",
                },
            )

        def _method_not_allowed(self) -> None:
            json_response(
                self,
                HTTPStatus.METHOD_NOT_ALLOWED,
                {"ok": False, "error": "method not allowed"},
            )

        def _dispatch(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
            payload = payload or {}

            if method == "GET" and path == "/health":
                return HTTPStatus.OK, {
                    "ok": True,
                    "service": "kde-agent-endpoint",
                    "public_network_exposure": False,
                }

            if method == "GET" and path == "/capabilities":
                probe = collect_probe(include_raw_introspection=False)
                probe["services"] = probe["services"][:100]
                return HTTPStatus.OK, {"ok": True, "capabilities": probe}

            if method == "GET" and path == "/kwin/current-desktop":
                status_payload, err = kwin_desktop_status()
                if err:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err}
                return HTTPStatus.OK, {
                    "ok": True,
                    "desktop": status_payload["current_desktop_number"],
                    "desktop_id": status_payload["current_desktop_id"],
                }

            if method == "GET" and path == "/kwin/desktops":
                status_payload, err = kwin_desktop_status()
                if err:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err}
                return HTTPStatus.OK, {"ok": True, "desktops": status_payload}

            if method == "GET" and path == "/kwin/objects":
                missing = require_cmd("qdbus6")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}
                code, out, err = run_cmd(["qdbus6", "org.kde.KWin"])
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                objects = [line.strip() for line in out.splitlines() if line.strip()]
                return HTTPStatus.OK, {"ok": True, "objects": objects}

            if method == "POST" and path in {"/kwin/set-desktop", "/kwin/desktop/switch"}:
                missing = require_cmd("qdbus6")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}
                desktop = payload.get("desktop")
                if not isinstance(desktop, int) or desktop < 1:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "desktop must be an integer >= 1"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/KWin",
                    "org.kde.KWin.setCurrentDesktop",
                    str(desktop),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                status_payload, status_err = kwin_desktop_status()
                if status_err:
                    return HTTPStatus.OK, {"ok": True, "result": out}
                return HTTPStatus.OK, {"ok": True, "result": out, "current": status_payload}

            if method == "POST" and path == "/kwin/desktop/create":
                position = payload.get("position")
                name = payload.get("name")
                if not isinstance(name, str) or not name.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "name must be a non-empty string"}
                if position is None:
                    status_payload, err = kwin_desktop_status()
                    if err:
                        return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err}
                    position = status_payload["count"]
                if not isinstance(position, int) or position < 0:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "position must be an integer >= 0"}

                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/VirtualDesktopManager",
                    "org.kde.KWin.VirtualDesktopManager.createDesktop",
                    str(position),
                    name.strip(),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                status_payload, status_err = kwin_desktop_status()
                if status_err:
                    return HTTPStatus.OK, {"ok": True, "result": out}
                return HTTPStatus.OK, {"ok": True, "result": out, "current": status_payload}

            if method == "POST" and path == "/kwin/desktop/rename":
                desktop_id = payload.get("desktop_id")
                name = payload.get("name")
                if not isinstance(desktop_id, str) or not desktop_id.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "desktop_id must be a non-empty string"}
                if not isinstance(name, str) or not name.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "name must be a non-empty string"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/VirtualDesktopManager",
                    "org.kde.KWin.VirtualDesktopManager.setDesktopName",
                    desktop_id.strip(),
                    name.strip(),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/kwin/desktop/remove":
                desktop_id = payload.get("desktop_id")
                if not isinstance(desktop_id, str) or not desktop_id.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "desktop_id must be a non-empty string"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/VirtualDesktopManager",
                    "org.kde.KWin.VirtualDesktopManager.removeDesktop",
                    desktop_id.strip(),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                status_payload, status_err = kwin_desktop_status()
                if status_err:
                    return HTTPStatus.OK, {"ok": True, "result": out}
                return HTTPStatus.OK, {"ok": True, "result": out, "current": status_payload}

            if method == "POST" and path == "/kwin/script/start":
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/Scripting",
                    "org.kde.kwin.Scripting.start",
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/kwin/script/is-loaded":
                plugin_name = payload.get("plugin_name")
                if not isinstance(plugin_name, str) or not plugin_name.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "plugin_name must be a non-empty string"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/Scripting",
                    "org.kde.kwin.Scripting.isScriptLoaded",
                    plugin_name.strip(),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "loaded": out.strip().lower() == "true", "raw": out}

            if method == "POST" and path == "/kwin/script/load":
                file_path = payload.get("file_path")
                plugin_name = payload.get("plugin_name")
                declarative = as_bool(payload.get("declarative"), default=False)
                if not isinstance(file_path, str) or not file_path.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "file_path must be a non-empty string"}
                method_name = "org.kde.kwin.Scripting.loadDeclarativeScript" if declarative else "org.kde.kwin.Scripting.loadScript"
                args = [file_path.strip()]
                if plugin_name is not None:
                    if not isinstance(plugin_name, str) or not plugin_name.strip():
                        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "plugin_name must be a non-empty string when provided"}
                    args.append(plugin_name.strip())
                code, out, err = run_qdbus("org.kde.KWin", "/Scripting", method_name, *args)
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out, "declarative": declarative}

            if method == "POST" and path == "/kwin/script/unload":
                plugin_name = payload.get("plugin_name")
                if not isinstance(plugin_name, str) or not plugin_name.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "plugin_name must be a non-empty string"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/Scripting",
                    "org.kde.kwin.Scripting.unloadScript",
                    plugin_name.strip(),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out, "unloaded": out.strip().lower() == "true"}

            if method == "POST" and path == "/kwin/effect/windowview":
                handles = payload.get("handles", [])
                if not isinstance(handles, list) or not all(isinstance(item, str) for item in handles):
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "handles must be an array of strings"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/org/kde/KWin/Effect/WindowView1",
                    "org.kde.KWin.Effect.WindowView1.activate",
                    *handles,
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/kwin/effect/highlight":
                windows = payload.get("windows", [])
                if not isinstance(windows, list) or not all(isinstance(item, str) for item in windows):
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "windows must be an array of strings"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/org/kde/KWin/HighlightWindow",
                    "org.kde.KWin.HighlightWindow.highlightWindows",
                    *windows,
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/kwin/nightlight/preview":
                temperature = payload.get("temperature")
                if not isinstance(temperature, int) or temperature < 1000 or temperature > 10000:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "temperature must be an integer between 1000 and 10000"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/org/kde/KWin/NightLight",
                    "org.kde.KWin.NightLight.preview",
                    str(temperature),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/kwin/nightlight/stop":
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/org/kde/KWin/NightLight",
                    "org.kde.KWin.NightLight.stopPreview",
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/kwin/nightlight/inhibit":
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/org/kde/KWin/NightLight",
                    "org.kde.KWin.NightLight.inhibit",
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "cookie": out}

            if method == "POST" and path == "/kwin/nightlight/uninhibit":
                cookie = payload.get("cookie")
                if not isinstance(cookie, int) or cookie < 0:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "cookie must be an integer >= 0"}
                code, out, err = run_qdbus(
                    "org.kde.KWin",
                    "/org/kde/KWin/NightLight",
                    "org.kde.KWin.NightLight.uninhibit",
                    str(cookie),
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/krunner/query":
                missing = require_cmd("qdbus6")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}
                term = payload.get("term")
                if not isinstance(term, str) or not term.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "term must be a non-empty string"}
                code, out, err = run_cmd(
                    ["qdbus6", "org.kde.krunner", "/App", "org.kde.krunner.App.query", term.strip()]
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/plasmashell/toggle-dashboard":
                missing = require_cmd("qdbus6")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}
                code, out, err = run_cmd(
                    ["qdbus6", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.toggleDashboard"]
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "POST" and path == "/notifications/notify":
                missing = require_cmd("gdbus")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}
                summary = payload.get("summary")
                body = payload.get("body", "")
                app_name = payload.get("app_name", "codex")
                timeout = payload.get("timeout", 5000)
                if not isinstance(summary, str) or not summary.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "summary must be a non-empty string"}
                if not isinstance(body, str):
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "body must be a string"}
                if not isinstance(app_name, str) or not app_name.strip():
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "app_name must be a non-empty string"}
                if not isinstance(timeout, int):
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "timeout must be an integer"}

                code, out, err = run_cmd(
                    [
                        "gdbus",
                        "call",
                        "--session",
                        "--dest",
                        "org.freedesktop.Notifications",
                        "--object-path",
                        "/org/freedesktop/Notifications",
                        "--method",
                        "org.freedesktop.Notifications.Notify",
                        app_name.strip(),
                        "0",
                        "",
                        summary.strip(),
                        body,
                        "[]",
                        "{}",
                        str(timeout),
                    ]
                )
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                return HTTPStatus.OK, {"ok": True, "result": out}

            if method == "GET" and path == "/screen/outputs":
                missing = require_cmd("kscreen-doctor")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}
                code, out, err = run_cmd(["kscreen-doctor", "-j"])
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}"}
                parsed: Any = out
                try:
                    parsed = json.loads(out)
                except json.JSONDecodeError:
                    parsed = out
                return HTTPStatus.OK, {"ok": True, "outputs": parsed}

            if method == "POST" and path == "/screen/apply":
                missing = require_cmd("kscreen-doctor")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}
                actions = payload.get("actions")
                if not isinstance(actions, list) or not actions:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "actions must be a non-empty array"}
                if not all(isinstance(item, str) and item.strip() for item in actions):
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "each action must be a non-empty string"}

                cmd = ["kscreen-doctor", *actions]
                code, out, err = run_cmd(cmd)
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}", "command": cmd}
                return HTTPStatus.OK, {"ok": True, "command": cmd, "result": out}

            if method == "GET" and path == "/config/read":
                missing = require_cmd("kreadconfig6")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}

                query = parse_qs(urlparse(self.path).query, keep_blank_values=True)
                group = query.get("group", [None])[0]
                key = query.get("key", [None])[0]
                file_name = query.get("file", [None])[0]
                default = query.get("default", [None])[0]

                if not group or not key:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "group and key query parameters are required"}

                valid, reason = validate_config_file(file_name)
                if not valid:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": reason}

                cmd = ["kreadconfig6"]
                if file_name:
                    cmd.extend(["--file", file_name])
                cmd.extend(["--group", group, "--key", key])
                if default is not None:
                    cmd.extend(["--default", default])

                code, out, err = run_cmd(cmd)
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}", "command": cmd}
                return HTTPStatus.OK, {"ok": True, "value": out}

            if method == "POST" and path == "/config/write":
                missing = require_cmd("kwriteconfig6")
                if missing:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": missing}

                group = payload.get("group")
                key = payload.get("key")
                value = payload.get("value")
                file_name = payload.get("file")
                value_type = payload.get("type")
                notify = as_bool(payload.get("notify"), default=False)

                if not isinstance(group, str) or not group:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "group must be a non-empty string"}
                if not isinstance(key, str) or not key:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "key must be a non-empty string"}
                if value is None:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "value is required"}

                valid, reason = validate_config_file(file_name)
                if not valid:
                    return HTTPStatus.BAD_REQUEST, {"ok": False, "error": reason}

                cmd = ["kwriteconfig6"]
                if file_name:
                    cmd.extend(["--file", file_name])
                cmd.extend(["--group", group, "--key", key])
                if value_type:
                    if value_type not in {"bool", "string"}:
                        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "type must be bool or string"}
                    cmd.extend(["--type", value_type])
                if notify:
                    cmd.append("--notify")
                cmd.append(str(value))

                code, out, err = run_cmd(cmd)
                if code != 0:
                    return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": err or out or f"exit code {code}", "command": cmd}
                return HTTPStatus.OK, {"ok": True, "command": cmd, "result": out}

            return HTTPStatus.NOT_FOUND, {"ok": False, "error": f"unknown endpoint: {path}"}

        def do_GET(self) -> None:
            if not self._authorize():
                self._reject_auth()
                return

            parsed = urlparse(self.path)
            status, payload = self._dispatch("GET", parsed.path)
            json_response(self, status, payload)

        def do_POST(self) -> None:
            if not self._authorize():
                self._reject_auth()
                return

            payload, err = read_json_body(self)
            if err:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": err})
                return

            parsed = urlparse(self.path)
            status, out_payload = self._dispatch("POST", parsed.path, payload)
            json_response(self, status, out_payload)

        def do_PUT(self) -> None:
            self._method_not_allowed()

        def do_PATCH(self) -> None:
            self._method_not_allowed()

        def do_DELETE(self) -> None:
            self._method_not_allowed()

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}\n")

    return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local KDE agent endpoint server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--token", default=os.getenv("KDE_AGENT_TOKEN"), help="Auth token (or set KDE_AGENT_TOKEN)")
    parser.add_argument(
        "--allow-no-token",
        action="store_true",
        help="Allow unauthenticated requests (use only on isolated local machines)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("Refusing non-local bind host. Use 127.0.0.1/localhost/::1.", file=sys.stderr)
        return 2

    token = args.token
    if not token and not args.allow_no_token:
        print("Missing token. Provide --token or KDE_AGENT_TOKEN, or use --allow-no-token for isolated debugging.", file=sys.stderr)
        return 2

    handler = make_handler(None if args.allow_no_token else token)
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print(f"kde-agent-endpoint listening on http://{args.host}:{args.port}")
    print("This server is intended for local desktop automation only.")
    if args.allow_no_token:
        print("WARNING: Authentication disabled.")

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
