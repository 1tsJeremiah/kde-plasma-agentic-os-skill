# Publishing to PyPI

This repository is configured for **Trusted Publishing** via GitHub OIDC.

Workflow file: `.github/workflows/publish-pypi.yml`

## One-time Setup (PyPI)

1. Sign in to PyPI.
2. Create project `kde-plasma-agentic-os-skill` (or create a pending publisher for that project name).
3. Add a trusted publisher with these values:

- Owner: `1tsJeremiah`
- Repository name: `kde-plasma-agentic-os-skill`
- Workflow name: `publish-pypi.yml`
- Environment name: `pypi`

## One-time Setup (GitHub)

1. In this repository, create Environment `pypi`.
2. Optionally add required reviewers for publish approvals.

No PyPI API token secret is required for trusted publishing.

## Release Flow

1. Bump version in:

- `pyproject.toml` -> `[project].version`
- `src/kde_plasma_agentic_os_installer/__init__.py` -> `__version__`

2. Commit and push `main`.
3. Create tag `vX.Y.Z` matching package version.
4. Create GitHub Release for that tag.
5. `Publish to PyPI` workflow runs automatically on release publish.

The workflow enforces tag/version match on release events.

## Manual Trigger

You can also run `Publish to PyPI` manually via `workflow_dispatch` after trusted publisher setup.

## Post-publish Verification

```bash
python3 -m pip index versions kde-plasma-agentic-os-skill
pipx install kde-plasma-agentic-os-skill
kde-plasma-skill --version
```
