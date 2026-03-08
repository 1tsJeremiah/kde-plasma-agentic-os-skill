#!/usr/bin/env python3
"""Control selected KWin effect interfaces on DBus."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from typing import List


def run_qdbus(args: List[str], timeout: int = 8) -> tuple[int, str, str]:
    if not shutil.which("qdbus6"):
        return 127, "", "qdbus6 not found"
    proc = subprocess.run(["qdbus6", *args], capture_output=True, text=True, timeout=timeout, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def require_success(code: int, out: str, err: str, action: str) -> str:
    if code != 0:
        raise RuntimeError(f"{action} failed: {err or out or f'exit code {code}'}")
    return out


def parse_csv(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Control KWin effects")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_windowview = sub.add_parser("windowview", help="Activate WindowView effect")
    p_windowview.add_argument("--handles", default="", help="Comma-separated window handles")

    p_highlight = sub.add_parser("highlight", help="Highlight windows")
    p_highlight.add_argument("--windows", default="", help="Comma-separated window ids/handles")

    p_night_preview = sub.add_parser("nightlight-preview", help="Preview Night Light temperature")
    p_night_preview.add_argument("temperature", type=int, help="Color temperature in kelvin")

    sub.add_parser("nightlight-stop", help="Stop Night Light preview")
    sub.add_parser("nightlight-inhibit", help="Inhibit Night Light transitions")

    p_uninhibit = sub.add_parser("nightlight-uninhibit", help="Release Night Light inhibit cookie")
    p_uninhibit.add_argument("cookie", type=int)

    args = parser.parse_args()

    try:
        if args.cmd == "windowview":
            handles = parse_csv(args.handles)
            code, out, err = run_qdbus(
                [
                    "org.kde.KWin",
                    "/org/kde/KWin/Effect/WindowView1",
                    "org.kde.KWin.Effect.WindowView1.activate",
                    *handles,
                ]
            )
            require_success(code, out, err, "windowview")
            print(f"WindowView activated for {len(handles)} handles")
            return 0

        if args.cmd == "highlight":
            windows = parse_csv(args.windows)
            code, out, err = run_qdbus(
                [
                    "org.kde.KWin",
                    "/org/kde/KWin/HighlightWindow",
                    "org.kde.KWin.HighlightWindow.highlightWindows",
                    *windows,
                ]
            )
            require_success(code, out, err, "highlight")
            print(f"Highlight requested for {len(windows)} windows")
            return 0

        if args.cmd == "nightlight-preview":
            code, out, err = run_qdbus(
                [
                    "org.kde.KWin",
                    "/org/kde/KWin/NightLight",
                    "org.kde.KWin.NightLight.preview",
                    str(args.temperature),
                ]
            )
            require_success(code, out, err, "nightlight-preview")
            print(f"Night Light preview set to {args.temperature}K")
            return 0

        if args.cmd == "nightlight-stop":
            code, out, err = run_qdbus(
                ["org.kde.KWin", "/org/kde/KWin/NightLight", "org.kde.KWin.NightLight.stopPreview"]
            )
            require_success(code, out, err, "nightlight-stop")
            print("Night Light preview stopped")
            return 0

        if args.cmd == "nightlight-inhibit":
            code, out, err = run_qdbus(
                ["org.kde.KWin", "/org/kde/KWin/NightLight", "org.kde.KWin.NightLight.inhibit"]
            )
            result = require_success(code, out, err, "nightlight-inhibit")
            print(f"Inhibit cookie: {result}")
            return 0

        if args.cmd == "nightlight-uninhibit":
            code, out, err = run_qdbus(
                [
                    "org.kde.KWin",
                    "/org/kde/KWin/NightLight",
                    "org.kde.KWin.NightLight.uninhibit",
                    str(args.cookie),
                ]
            )
            require_success(code, out, err, "nightlight-uninhibit")
            print(f"Released cookie {args.cookie}")
            return 0

    except RuntimeError as exc:
        parser.error(str(exc))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
