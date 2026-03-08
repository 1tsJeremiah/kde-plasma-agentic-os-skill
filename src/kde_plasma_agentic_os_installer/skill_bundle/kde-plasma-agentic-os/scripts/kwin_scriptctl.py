#!/usr/bin/env python3
"""Manage KWin scripts through the org.kde.kwin.Scripting interface."""

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


def main() -> int:
    parser = argparse.ArgumentParser(description="KWin scripting control")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("start", help="Start loaded scripts")

    p_is = sub.add_parser("is-loaded", help="Check whether plugin is loaded")
    p_is.add_argument("plugin_name")

    p_load = sub.add_parser("load", help="Load JavaScript script file")
    p_load.add_argument("file_path")
    p_load.add_argument("--plugin-name", default=None)

    p_load_decl = sub.add_parser("load-declarative", help="Load declarative script")
    p_load_decl.add_argument("file_path")
    p_load_decl.add_argument("--plugin-name", default=None)

    p_unload = sub.add_parser("unload", help="Unload script plugin")
    p_unload.add_argument("plugin_name")

    args = parser.parse_args()

    try:
        if args.cmd == "start":
            code, out, err = run_qdbus(["org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.start"])
            require_success(code, out, err, "start")
            print("Started KWin scripts")
            return 0

        if args.cmd == "is-loaded":
            code, out, err = run_qdbus(
                [
                    "org.kde.KWin",
                    "/Scripting",
                    "org.kde.kwin.Scripting.isScriptLoaded",
                    args.plugin_name,
                ]
            )
            value = require_success(code, out, err, "is-loaded")
            print(value)
            return 0

        if args.cmd == "load":
            qargs = ["org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", args.file_path]
            if args.plugin_name:
                qargs.append(args.plugin_name)
            code, out, err = run_qdbus(qargs)
            result = require_success(code, out, err, "load")
            print(f"load result: {result}")
            return 0

        if args.cmd == "load-declarative":
            qargs = ["org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadDeclarativeScript", args.file_path]
            if args.plugin_name:
                qargs.append(args.plugin_name)
            code, out, err = run_qdbus(qargs)
            result = require_success(code, out, err, "load-declarative")
            print(f"load result: {result}")
            return 0

        if args.cmd == "unload":
            code, out, err = run_qdbus(
                ["org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", args.plugin_name]
            )
            result = require_success(code, out, err, "unload")
            print(result)
            return 0

    except RuntimeError as exc:
        parser.error(str(exc))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
