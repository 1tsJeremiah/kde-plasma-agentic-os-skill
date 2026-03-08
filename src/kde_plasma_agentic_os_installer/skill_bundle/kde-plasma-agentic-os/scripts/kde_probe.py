#!/usr/bin/env python3
"""Inspect KDE Plasma runtime capabilities and expose a machine-readable summary."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

TARGETS = [
    ("org.kde.plasmashell", "/PlasmaShell"),
    ("org.kde.KWin", "/KWin"),
    ("org.kde.krunner", "/App"),
    ("org.freedesktop.Notifications", "/org/freedesktop/Notifications"),
    ("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"),
    ("org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement"),
]

COMMANDS = [
    "qdbus6",
    "gdbus",
    "dbus-send",
    "busctl",
    "kreadconfig6",
    "kwriteconfig6",
    "kscreen-doctor",
    "nmcli",
    "pactl",
    "systemctl",
]


@dataclass
class CmdResult:
    code: int
    stdout: str
    stderr: str


def run_cmd(cmd: List[str], timeout: int = 5) -> CmdResult:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CmdResult(proc.returncode, proc.stdout.strip(), proc.stderr.strip())
    except Exception as exc:  # pragma: no cover - defensive path
        return CmdResult(1, "", str(exc))


def parse_methods(introspection_output: str) -> Dict[str, List[str]]:
    methods: Dict[str, List[str]] = {}
    current_iface: Optional[str] = None
    in_methods = False

    for line in introspection_output.splitlines():
        iface_match = re.match(r"^\s*interface\s+([^\s{]+)\s*{", line)
        if iface_match:
            current_iface = iface_match.group(1)
            methods.setdefault(current_iface, [])
            in_methods = False
            continue

        stripped = line.strip()
        if stripped == "methods:":
            in_methods = True
            continue
        if stripped in {"signals:", "properties:"}:
            in_methods = False
            continue

        if in_methods and current_iface:
            method_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\(", line)
            if method_match:
                methods[current_iface].append(method_match.group(1))

    return {k: v for k, v in methods.items() if v}


def list_services() -> Tuple[List[str], str]:
    if shutil.which("qdbus6"):
        res = run_cmd(["qdbus6"], timeout=8)
        if res.code == 0:
            services = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            return sorted(set(services)), "qdbus6"

    if shutil.which("busctl"):
        res = run_cmd(["busctl", "--user", "list", "--no-pager"], timeout=8)
        if res.code == 0:
            services: List[str] = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("NAME"):
                    continue
                parts = line.split()
                if parts:
                    services.append(parts[0])
            return sorted(set(services)), "busctl"

    return [], "none"


def introspect(service: str, path: str) -> Dict[str, object]:
    if not shutil.which("gdbus"):
        return {
            "available": False,
            "reason": "gdbus not found",
            "interfaces": {},
            "methods": {},
        }

    res = run_cmd(
        [
            "gdbus",
            "introspect",
            "--session",
            "--dest",
            service,
            "--object-path",
            path,
        ],
        timeout=8,
    )

    if res.code != 0:
        return {
            "available": False,
            "reason": res.stderr or res.stdout or f"exit code {res.code}",
            "interfaces": {},
            "methods": {},
        }

    method_map = parse_methods(res.stdout)
    return {
        "available": True,
        "interfaces": sorted(method_map.keys()),
        "methods": method_map,
        "raw_excerpt": "\n".join(res.stdout.splitlines()[:120]),
    }


def collect_probe(include_raw_introspection: bool = False) -> Dict[str, object]:
    commands = {name: shutil.which(name) for name in COMMANDS}
    services, source = list_services()

    targets: Dict[str, Dict[str, object]] = {}
    for service, path in TARGETS:
        key = f"{service}:{path}"
        record = introspect(service, path)
        if not include_raw_introspection and "raw_excerpt" in record:
            record.pop("raw_excerpt", None)
        targets[key] = record

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "session": {
            "XDG_CURRENT_DESKTOP": os.getenv("XDG_CURRENT_DESKTOP"),
            "XDG_SESSION_TYPE": os.getenv("XDG_SESSION_TYPE"),
            "DESKTOP_SESSION": os.getenv("DESKTOP_SESSION"),
        },
        "commands": commands,
        "service_listing_source": source,
        "service_count": len(services),
        "services": services,
        "targets": targets,
    }


def print_human_readable(data: Dict[str, object]) -> None:
    print("KDE Plasma Probe")
    print(f"Generated: {data['generated_at_utc']}")
    print("")

    session = data["session"]
    print("Session:")
    for key, value in session.items():
        print(f"- {key}: {value}")
    print("")

    print("Commands:")
    for cmd, path in data["commands"].items():
        status = path if path else "missing"
        print(f"- {cmd}: {status}")
    print("")

    print(f"D-Bus services ({data['service_count']} total, source={data['service_listing_source']}):")
    for svc in list(data["services"])[:30]:
        print(f"- {svc}")
    if data["service_count"] > 30:
        print(f"- ... ({data['service_count'] - 30} more)")
    print("")

    print("Target interfaces:")
    for target, details in data["targets"].items():
        available = details.get("available")
        print(f"- {target}: {'available' if available else 'unavailable'}")
        if available:
            interfaces = details.get("interfaces", [])
            if interfaces:
                print(f"  interfaces: {', '.join(interfaces)}")
            methods = details.get("methods", {})
            concise = []
            for iface, method_names in methods.items():
                if method_names:
                    concise.append(f"{iface}[{', '.join(method_names[:6])}{'...' if len(method_names) > 6 else ''}]")
            if concise:
                print(f"  methods: {' | '.join(concise)}")
        else:
            reason = details.get("reason")
            if reason:
                print(f"  reason: {reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe KDE Plasma automation surfaces")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument(
        "--raw-introspection",
        action="store_true",
        help="Include introspection excerpts in JSON output",
    )
    args = parser.parse_args()

    data = collect_probe(include_raw_introspection=args.raw_introspection)

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_human_readable(data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
