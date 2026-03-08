#!/usr/bin/env python3
"""Control KWin virtual desktops through DBus."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List

DESKTOP_RE = re.compile(r"\[Argument: \(uss\)\s*(\d+),\s*\"([^\"]+)\",\s*\"([^\"]*)\"\]")


@dataclass
class CmdResult:
    code: int
    stdout: str
    stderr: str


def run_qdbus(args: List[str], literal: bool = False, timeout: int = 8) -> CmdResult:
    if not shutil.which("qdbus6"):
        return CmdResult(127, "", "qdbus6 not found")

    cmd = ["qdbus6"]
    if literal:
        cmd.append("--literal")
    cmd.extend(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return CmdResult(proc.returncode, proc.stdout.strip(), proc.stderr.strip())


def parse_desktops(literal_output: str) -> List[dict]:
    desktops = []
    for order, desk_id, name in DESKTOP_RE.findall(literal_output):
        desktops.append({"order": int(order), "id": desk_id, "name": name})
    return sorted(desktops, key=lambda item: item["order"])


def get_status() -> dict:
    count = run_qdbus(["org.kde.KWin", "/VirtualDesktopManager", "org.kde.KWin.VirtualDesktopManager.count"])
    current_num = run_qdbus(["org.kde.KWin", "/KWin", "org.kde.KWin.currentDesktop"])
    current_id = run_qdbus(["org.kde.KWin", "/VirtualDesktopManager", "org.kde.KWin.VirtualDesktopManager.current"])
    desktops_raw = run_qdbus(
        ["org.kde.KWin", "/VirtualDesktopManager", "org.kde.KWin.VirtualDesktopManager.desktops"],
        literal=True,
    )

    failures = [r for r in [count, current_num, current_id, desktops_raw] if r.code != 0]
    if failures:
        first = failures[0]
        raise RuntimeError(first.stderr or first.stdout or f"qdbus6 failed with code {first.code}")

    return {
        "count": int(count.stdout),
        "current_desktop_number": int(current_num.stdout),
        "current_desktop_id": current_id.stdout,
        "desktops": parse_desktops(desktops_raw.stdout),
    }


def cmd_status(as_json: bool) -> int:
    status = get_status()
    if as_json:
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0

    print(f"Desktop count: {status['count']}")
    print(f"Current desktop number: {status['current_desktop_number']}")
    print(f"Current desktop id: {status['current_desktop_id']}")
    print("Desktops:")
    for desk in status["desktops"]:
        marker = "*" if desk["id"] == status["current_desktop_id"] else " "
        print(f"{marker} {desk['order'] + 1}: {desk['name']} ({desk['id']})")
    return 0


def cmd_switch(desktop_number: int) -> int:
    status = get_status()
    if desktop_number < 1 or desktop_number > status["count"]:
        raise RuntimeError(f"desktop must be in range 1..{status['count']}")

    res = run_qdbus(["org.kde.KWin", "/KWin", "org.kde.KWin.setCurrentDesktop", str(desktop_number)])
    if res.code != 0:
        raise RuntimeError(res.stderr or res.stdout or f"switch failed with code {res.code}")

    updated = get_status()
    print(f"Switched to desktop {updated['current_desktop_number']} ({updated['current_desktop_id']})")
    return 0


def cmd_create(name: str, position: int | None) -> int:
    status = get_status()
    pos = status["count"] if position is None else position
    if pos < 0:
        raise RuntimeError("position must be >= 0")

    res = run_qdbus(["org.kde.KWin", "/VirtualDesktopManager", "org.kde.KWin.VirtualDesktopManager.createDesktop", str(pos), name])
    if res.code != 0:
        raise RuntimeError(res.stderr or res.stdout or f"create failed with code {res.code}")

    print("Desktop created")
    return cmd_status(as_json=False)


def cmd_rename(desktop_id: str, name: str) -> int:
    res = run_qdbus(["org.kde.KWin", "/VirtualDesktopManager", "org.kde.KWin.VirtualDesktopManager.setDesktopName", desktop_id, name])
    if res.code != 0:
        raise RuntimeError(res.stderr or res.stdout or f"rename failed with code {res.code}")
    print(f"Renamed desktop {desktop_id} to '{name}'")
    return 0


def cmd_remove(desktop_id: str) -> int:
    res = run_qdbus(["org.kde.KWin", "/VirtualDesktopManager", "org.kde.KWin.VirtualDesktopManager.removeDesktop", desktop_id])
    if res.code != 0:
        raise RuntimeError(res.stderr or res.stdout or f"remove failed with code {res.code}")
    print(f"Removed desktop {desktop_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage KWin virtual desktops")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="Show desktop status")
    p_status.add_argument("--json", action="store_true", help="Emit JSON")

    p_switch = sub.add_parser("switch", help="Switch to desktop number (1-based)")
    p_switch.add_argument("desktop", type=int, help="Desktop number")

    p_create = sub.add_parser("create", help="Create a virtual desktop")
    p_create.add_argument("name", help="Desktop name")
    p_create.add_argument("--position", type=int, default=None, help="0-based insertion position")

    p_rename = sub.add_parser("rename", help="Rename a virtual desktop by id")
    p_rename.add_argument("desktop_id", help="Desktop UUID")
    p_rename.add_argument("name", help="New desktop name")

    p_remove = sub.add_parser("remove", help="Remove a virtual desktop by id")
    p_remove.add_argument("desktop_id", help="Desktop UUID")

    args = parser.parse_args()

    try:
        if args.cmd == "status":
            return cmd_status(as_json=args.json)
        if args.cmd == "switch":
            return cmd_switch(args.desktop)
        if args.cmd == "create":
            return cmd_create(args.name, args.position)
        if args.cmd == "rename":
            return cmd_rename(args.desktop_id, args.name)
        if args.cmd == "remove":
            return cmd_remove(args.desktop_id)
    except RuntimeError as exc:
        parser.error(str(exc))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
