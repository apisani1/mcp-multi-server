---
description: Audit, plan, execute, verify, or rollback an MCP Python SDK v1.x → v1.x migration.
argument-hint: <mode> [from_version] [to_version] [--ci] [--json]
---

# /sdk-migration-manager

Thin wrapper that activates the `sdk-migration-manager` skill with parsed positional
arguments. All business logic lives in the skill — this command is responsible only for
argument parsing and delegating.

## Usage

```
/sdk-migration-manager <mode> [from_version] [to_version] [--ci] [--json]
```

- `<mode>` — required. One of `audit | plan | execute | verify | rollback`.
- `[from_version]` / `[to_version]` — optional. If absent, the skill auto-detects
  `from_version` from `pyproject.toml` / `uv.lock` / `poetry.lock` and defaults
  `to_version` to the latest stable on the v1.x maintenance branch.
- `--ci` — headless mode. Suppresses interactive prompts; non-zero exit on blockers.
- `--json` — emit `risks.json` payload to stdout in addition to writing artifacts.

If `<mode>` is missing or not one of the five valid values, print usage and exit non-interactively
(exit code 2 under `--ci`).

## Examples

```
/sdk-migration-manager audit
/sdk-migration-manager audit 1.13 1.27
/sdk-migration-manager plan 1.13.1 1.27.1
/sdk-migration-manager execute
/sdk-migration-manager verify
/sdk-migration-manager rollback
/sdk-migration-manager audit --ci --json
```

## What this command does

Parse the arguments above, then invoke the `sdk-migration-manager` skill with the parsed
values. The skill handles version detection, subagent dispatch, scanning, artifact
generation, and exit codes. See `.claude/skills/sdk-migration-manager/SKILL.md` for the
full behavior contract.

## Arguments passed to skill

User invocation: `$ARGUMENTS`

Activate the `sdk-migration-manager` skill and pass these arguments through. Parse:
1. First positional → `mode` (required; reject if not in `{audit, plan, execute, verify, rollback}`)
2. Second positional (if present) → `from_version`
3. Third positional (if present) → `to_version`
4. `--ci` and `--json` are flags; forward them to the skill.

If the user invoked without any arguments, the skill should print usage and exit (exit 2
in `--ci`).

## Notes

- `execute` mode operates **in place** on `.claude/migration-reports/latest/`. It requires
  a `plan.md` produced by a prior `plan` run. If that's missing, the command fails fast.
- Once `verify` runs after `execute`, the `latest` pointer advances to the verify run.
  To resume `execute` against the original plan, re-run `plan` (or pass the explicit
  run directory path).
