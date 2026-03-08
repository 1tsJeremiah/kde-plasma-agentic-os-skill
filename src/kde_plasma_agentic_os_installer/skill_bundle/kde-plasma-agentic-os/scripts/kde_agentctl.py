#!/usr/bin/env python3
"""Minimal client for kde_agent_endpoint.py."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call local KDE agent endpoints")
    parser.add_argument("method", choices=["GET", "POST"], help="HTTP method")
    parser.add_argument("path", help="Endpoint path (for example /health)")
    parser.add_argument("--base-url", default=os.getenv("KDE_AGENT_BASE_URL", "http://127.0.0.1:8765"))
    parser.add_argument("--token", default=os.getenv("KDE_AGENT_TOKEN"), help="Auth token")
    parser.add_argument("--query", action="append", default=[], help="Query string pair key=value (repeatable)")
    parser.add_argument("--json", default="{}", help="JSON body for POST")
    return parser.parse_args()


def build_url(base_url: str, path: str, query_pairs: list[str]) -> str:
    query = {}
    for pair in query_pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid query pair '{pair}', expected key=value")
        key, value = pair.split("=", 1)
        query.setdefault(key, []).append(value)

    normalized_path = path if path.startswith("/") else f"/{path}"
    query_string = urllib.parse.urlencode(query, doseq=True)
    if query_string:
        return f"{base_url.rstrip('/')}{normalized_path}?{query_string}"
    return f"{base_url.rstrip('/')}{normalized_path}"


def main() -> int:
    args = parse_args()

    try:
        url = build_url(args.base_url, args.path, args.query)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    body: bytes | None = None
    headers = {"Accept": "application/json"}

    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    if args.method == "POST":
        try:
            parsed = json.loads(args.json)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON body: {exc}", file=sys.stderr)
            return 2
        body = json.dumps(parsed).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=body, method=args.method, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            payload = resp.read().decode("utf-8")
            print(payload)
            return 0
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(error_body, file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
