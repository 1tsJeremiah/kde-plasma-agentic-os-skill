#!/usr/bin/env python3
"""CLI for installing and managing the KDE Plasma Agentic OS Codex skill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from importlib.resources import as_file, files
from pathlib import Path
from typing import Dict, Iterable

from . import __version__

SKILL_NAME = "kde-plasma-agentic-os"


def _bundle_path() -> object:
    return files("kde_plasma_agentic_os_installer").joinpath("skill_bundle", SKILL_NAME)


def _default_dest() -> Path:
    return Path.home() / ".codex" / "skills"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def _ensure_exec_bits(skill_dir: Path) -> None:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return
    for path in scripts_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".sh", ".py"}:
            path.chmod(path.stat().st_mode | 0o100)


def install_skill(dest_root: Path, force: bool) -> Path:
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / SKILL_NAME

    if dest.exists():
        if not force:
            raise RuntimeError(f"Destination exists: {dest}. Use --force to replace it.")
        shutil.rmtree(dest)

    with as_file(_bundle_path()) as src:
        shutil.copytree(Path(src), dest)

    _ensure_exec_bits(dest)
    return dest


def _service_script(skill_dir: Path, uninstall: bool = False) -> Path:
    name = "uninstall_user_service.sh" if uninstall else "install_user_service.sh"
    return skill_dir / "scripts" / name


def install_service(skill_dir: Path) -> None:
    script = _service_script(skill_dir)
    if not script.exists():
        raise RuntimeError(f"Service installer not found: {script}")
    _run(["bash", str(script)], check=True)


def uninstall_service(skill_dir: Path) -> None:
    script = _service_script(skill_dir, uninstall=True)
    if not script.exists():
        raise RuntimeError(f"Service uninstaller not found: {script}")
    _run(["bash", str(script)], check=True)


def doctor(skill_dir: Path) -> Dict[str, object]:
    required = ["qdbus6", "gdbus", "kreadconfig6", "kwriteconfig6", "kscreen-doctor", "systemctl"]
    commands = {cmd: shutil.which(cmd) for cmd in required}

    result: Dict[str, object] = {
        "skill_dir": str(skill_dir),
        "skill_exists": skill_dir.exists(),
        "required_commands": commands,
        "systemd_user_enabled": None,
        "systemd_user_active": None,
        "endpoint_health": None,
    }

    if shutil.which("systemctl"):
        enabled = _run(["systemctl", "--user", "is-enabled", "kde-agent-endpoint.service"], check=False)
        active = _run(["systemctl", "--user", "is-active", "kde-agent-endpoint.service"], check=False)
        result["systemd_user_enabled"] = enabled.stdout.strip() if enabled.stdout else enabled.stderr.strip()
        result["systemd_user_active"] = active.stdout.strip() if active.stdout else active.stderr.strip()

    env_file = Path.home() / ".config" / "mindstack" / "kde-agent-endpoint.env"
    if env_file.exists():
        env_map = parse_env_file(env_file)
        token = env_map.get("KDE_AGENT_TOKEN")
        host = env_map.get("KDE_AGENT_HOST", "127.0.0.1")
        port = env_map.get("KDE_AGENT_PORT", "8765")
        if token and shutil.which("python3"):
            ctl = skill_dir / "scripts" / "kde_agentctl.py"
            if ctl.exists():
                health = _run(
                    [
                        "python3",
                        str(ctl),
                        "GET",
                        "/health",
                        "--token",
                        token,
                        "--base-url",
                        f"http://{host}:{port}",
                    ],
                    check=False,
                )
                result["endpoint_health"] = health.stdout.strip() or health.stderr.strip()

    return result


def parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def print_result(data: Dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    for key, value in data.items():
        print(f"{key}: {value}")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="kde-plasma-skill", description="Install and manage KDE Plasma Agentic OS skill")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Install bundled skill into Codex skills directory")
    p_install.add_argument("--dest", default=str(_default_dest()), help="Destination skills root directory")
    p_install.add_argument("--force", action="store_true", help="Replace existing destination directory")
    p_install.add_argument("--with-service", action="store_true", help="Install and start user systemd endpoint service")

    p_service_install = sub.add_parser("service-install", help="Install/start user systemd service")
    p_service_install.add_argument("--skill-path", default=str(_default_dest() / SKILL_NAME), help="Installed skill path")

    p_service_uninstall = sub.add_parser("service-uninstall", help="Stop/disable user systemd service")
    p_service_uninstall.add_argument("--skill-path", default=str(_default_dest() / SKILL_NAME), help="Installed skill path")

    p_doctor = sub.add_parser("doctor", help="Inspect host prerequisites and endpoint status")
    p_doctor.add_argument("--skill-path", default=str(_default_dest() / SKILL_NAME), help="Installed skill path")
    p_doctor.add_argument("--json", action="store_true", help="Print JSON output")

    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        if args.command == "install":
            installed = install_skill(Path(args.dest).expanduser(), force=args.force)
            print(f"Installed skill at: {installed}")
            if args.with_service:
                install_service(installed)
                print("Installed and started kde-agent-endpoint.service")
            return 0

        if args.command == "service-install":
            install_service(Path(args.skill_path).expanduser())
            print("Installed and started kde-agent-endpoint.service")
            return 0

        if args.command == "service-uninstall":
            uninstall_service(Path(args.skill_path).expanduser())
            print("Stopped and removed kde-agent-endpoint.service unit")
            return 0

        if args.command == "doctor":
            data = doctor(Path(args.skill_path).expanduser())
            print_result(data, as_json=args.json)
            return 0

    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or str(exc)
        print(detail, file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
