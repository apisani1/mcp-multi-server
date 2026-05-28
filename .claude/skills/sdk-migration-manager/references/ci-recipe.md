# CI Integration Recipe

The skill ships no CI YAML. This file describes how to wire it into a CI step yourself.
Keep it lean — the goal is a gate that fails the build when blockers are found, not a
full migration pipeline.

## Headless contract

Inputs:
- `MCP_FROM_VERSION` — env var or CLI arg
- `MCP_TO_VERSION` — env var or CLI arg
- `MCP_MODE` — env var, usually `audit` or `verify`
- `--ci` — flag, suppresses interactive prompts
- `--json` — flag, emits `risks.json` to stdout in addition to writing the artifact

Exit codes:
- `0` — clean (no blockers; advisories OK)
- `1` — blockers found
- `2` — configuration error (e.g., undetectable `from_version`)

## Minimal GitHub Actions step

```yaml
- name: MCP SDK migration audit
  env:
    MCP_FROM_VERSION: ${{ vars.MCP_FROM_VERSION }}  # e.g. 1.13.1
    MCP_TO_VERSION:   ${{ vars.MCP_TO_VERSION }}    # e.g. 1.27.1
    MCP_MODE: audit
  run: |
    claude-code skill run sdk-migration-manager --ci --json > risks.json
    jq '.findings | map(select(.severity == "blocker")) | length' risks.json
- name: Upload migration report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: mcp-migration-report
    path: .claude/migration-reports/
```

## GitLab CI step

```yaml
mcp-audit:
  stage: lint
  variables:
    MCP_FROM_VERSION: "1.13.1"
    MCP_TO_VERSION: "1.27.1"
    MCP_MODE: audit
  script:
    - claude-code skill run sdk-migration-manager --ci --json > risks.json
  artifacts:
    when: always
    paths:
      - .claude/migration-reports/
      - risks.json
```

## Pre-merge gate vs. nightly audit

Two common patterns:

1. **Pre-merge gate.** Run `audit` on every PR. Fail the build on `severity == blocker`.
   Allow `risk` / `advisory` through. Cheap (no subagents, just pattern scans).
2. **Nightly full audit.** Run `audit` on `main` with subagents enabled. Post a Slack
   summary listing top findings. Useful for tracking SEP-986 / Tasks-adoption drift over
   time.

## Verify in release pipelines

Post-deploy or post-upgrade, run `verify` against the deployed code (or against `HEAD`
in CI) and gate the release on a clean exit code:

```bash
claude-code skill run sdk-migration-manager --ci -- verify "1.13.1" "1.27.1"
```

## Tips

- Pin the skill version (the contents of `.claude/skills/sdk-migration-manager/`) to the
  repo, so the audit logic doesn't drift between CI and local runs.
- Keep `notes/mcp-python-sdk-1_13_1-to-1_27_1_migration_guide.md` in the repo. The skill
  re-reads it on every run; if it moves, the audit becomes generic.
- Don't run subagents in CI unless they're checked into `.claude/agents/`. The skill
  falls back to inline checks when subagents aren't present, which is the right CI
  default.
