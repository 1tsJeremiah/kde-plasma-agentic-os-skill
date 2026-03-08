# Contributing

## Scope

Contribute improvements to:

- Skill guidance (`SKILL.md`, references)
- Endpoint safety and allowlisted operations
- KDE/KWin automation helpers
- Packaging and installer UX

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e .
```

## Validation

```bash
python3 -m py_compile src/kde_plasma_agentic_os_installer/cli.py
python3 -m py_compile src/kde_plasma_agentic_os_installer/skill_bundle/kde-plasma-agentic-os/scripts/*.py
kde-plasma-skill --help
```

## Pull Request Guidance

- Keep endpoint additions allowlisted and explicit.
- Include before/after behavior notes for changed endpoints.
- Avoid introducing remote/public service patterns.
- Update `README.md` when command flows change.
