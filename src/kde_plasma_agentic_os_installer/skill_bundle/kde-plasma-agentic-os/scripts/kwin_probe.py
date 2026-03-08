#!/usr/bin/env python3
"""Inspect KWin automation interfaces and summarize available methods."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Tuple

TARGET_PATHS = [
    "/KWin",
    "/Scripting",
    "/VirtualDesktopManager",
    "/org/kde/KWin/Effect/WindowView1",
    "/org/kde/KWin/HighlightWindow",
    "/org/kde/KWin/NightLight",
    "/org/kde/KWin/ScreenShot2",
]


def run_cmd(cmd: List[str], timeout: int = 8) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def parse_methods_and_properties(text: str) -> Dict[str, Dict[str, List[str]]]:
    out: Dict[str, Dict[str, List[str]]] = {}
    current_iface = None
    mode = None

    for line in text.splitlines():
        m = re.match(r"^\s*interface\s+([^\s{]+)\s*{", line)
        if m:
            current_iface = m.group(1)
            out.setdefault(current_iface, {"methods": [], "properties": []})
            mode = None
            continue

        stripped = line.strip()
        if stripped == "methods:":
            mode = "methods"
            continue
        if stripped == "properties:":
            mode = "properties"
            continue
        if stripped == "signals:":
            mode = "signals"
            continue

        if not current_iface or mode not in {"methods", "properties"}:
            continue

        if mode == "methods":
            mm = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\(", line)
            if mm:
                out[current_iface]["methods"].append(mm.group(1))

        if mode == "properties":
            pm = re.match(r"^\s*(?:readonly|readwrite)\s+[^\s]+\s+([A-Za-z_][A-Za-z0-9_]*)", line)
            if pm:
                out[current_iface]["properties"].append(pm.group(1))

    return {k: v for k, v in out.items() if v["methods"] or v["properties"]}


def list_paths() -> List[str]:
    if not shutil.which("qdbus6"):
        return []
    code, out, _ = run_cmd(["qdbus6", "org.kde.KWin"]) 
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def introspect(path: str) -> Dict[str, object]:
    if not shutil.which("gdbus"):
        return {"available": False, "error": "gdbus not found"}

    code, out, err = run_cmd(
        [
            "gdbus",
            "introspect",
            "--session",
            "--dest",
            "org.kde.KWin",
            "--object-path",
            path,
        ]
    )
    if code != 0:
        return {"available": False, "error": err or out or f"exit code {code}"}

    parsed = parse_methods_and_properties(out)
    return {
        "available": True,
        "interfaces": sorted(parsed.keys()),
        "details": parsed,
    }


def collect() -> Dict[str, object]:
    paths = list_paths()
    targets = {path: introspect(path) for path in TARGET_PATHS}

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "session": {
            "XDG_CURRENT_DESKTOP": os.getenv("XDG_CURRENT_DESKTOP"),
            "XDG_SESSION_TYPE": os.getenv("XDG_SESSION_TYPE"),
            "DESKTOP_SESSION": os.getenv("DESKTOP_SESSION"),
        },
        "commands": {name: shutil.which(name) for name in ["qdbus6", "gdbus"]},
        "kwin_path_count": len(paths),
        "kwin_paths": paths,
        "targets": targets,
    }


def print_human(data: Dict[str, object]) -> None:
    print("KWin Probe")
    print(f"Generated: {data['generated_at_utc']}")
    print("")
    print("Session:")
    for key, value in data["session"].items():
        print(f"- {key}: {value}")
    print("")
    print(f"KWin object paths: {data['kwin_path_count']}")
    for path in data["kwin_paths"][:40]:
        print(f"- {path}")
    if data["kwin_path_count"] > 40:
        print(f"- ... ({data['kwin_path_count'] - 40} more)")
    print("")

    print("Target interfaces:")
    for path, details in data["targets"].items():
        print(f"- {path}: {'available' if details.get('available') else 'unavailable'}")
        if details.get("available"):
            for iface, iface_data in details.get("details", {}).items():
                methods = iface_data.get("methods", [])
                props = iface_data.get("properties", [])
                if methods:
                    print(f"  {iface} methods: {', '.join(methods[:8])}{'...' if len(methods) > 8 else ''}")
                if props:
                    print(f"  {iface} properties: {', '.join(props[:8])}{'...' if len(props) > 8 else ''}")
        else:
            print(f"  error: {details.get('error')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe KWin DBus interfaces")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    data = collect()
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_human(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
