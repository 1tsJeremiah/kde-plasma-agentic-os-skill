# Community Pipeline

This folder documents automated community intake and planning signals.

## Active Automations

- `community-intake.yml`: auto-triage labels and first response on issue intake.
- `community-digest.yml`: weekly summary comment with open demand by category.

`community-intake.yml` infers `kind:*` labels from title prefixes (`[Scale]`, `[Idea]`, `[Package Expansion]`, `[Bug]`) when issues are not created via forms.

## Categories

- `kind:scale-request`
- `kind:idea`
- `kind:package-expansion`
- `kind:bug`

These labels are used for backlog shaping and expansion planning.
