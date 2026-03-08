# Security Policy

## Supported Version

- `main` branch is supported.

## Reporting a Vulnerability

Open a private security advisory or contact the maintainers directly.

## Secure Defaults

This project intentionally enforces:

- Localhost-only endpoint binding
- Token authentication by default
- No generic command execution endpoint
- Allowlisted operation surface only

## Operational Recommendations

- Keep `~/.config/mindstack/kde-agent-endpoint.env` permissions at `600`.
- Rotate `KDE_AGENT_TOKEN` regularly.
- Do not expose the local endpoint through Cloudflare Tunnel, reverse proxy, or router port-forwarding.
- Audit endpoint additions for privilege escalation and injection risks.
