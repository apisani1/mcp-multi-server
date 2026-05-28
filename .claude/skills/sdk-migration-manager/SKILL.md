---
name: sdk-migration-manager
description: |
  Plan, execute, and validate MCP Python SDK v1.x → v1.x migrations. Activate when
  the user mentions upgrading the `mcp` Python package, migrating between SDK versions
  (e.g. 1.13 → 1.27), auditing MCP usage for breaking changes, or producing a migration
  plan / checklist / risk report. Use this skill whenever you see phrases like
  "upgrade mcp", "migrate mcp sdk", "mcp 1.x → 1.y", "mcp migration plan",
  "audit mcp usage", "is my repo ready for mcp X", "mcp upgrade risks", or
  "mcp sdk modernization" — even if the user doesn't explicitly ask for a "migration".
  Scope is v1.x → v1.x only; v1 → v2 is out of scope until the v2 SDK stabilizes.
---

# sdk-migration-manager

Production-grade orchestrator for MCP Python SDK v1.x → v1.x migrations. Audits a target
repository, builds a phased plan, walks the team through execution with checkpoints,
verifies post-upgrade conformance, and produces a rollback recipe when needed.

The 1.13.1 → 1.27.1 upgrade is the default worked example. Other v1.x version pairs use
the same workflow with per-version heuristics extracted from
[the MCP Python SDK release notes](https://github.com/modelcontextprotocol/python-sdk/releases).
v1 → v2 is explicitly out of scope.

## Inputs

| Param | Purpose | Default |
|---|---|---|
| `from_version` | Source SDK version | Detect from `pyproject.toml` (Poetry or PEP 621), `uv.lock`, or `poetry.lock`. Error in `--ci` mode if undetectable. |
| `to_version` | Target SDK version | Latest stable on the v1.x maintenance branch (currently 1.27.x). |
| `mode` | `audit \| plan \| execute \| verify \| rollback` | `audit` |
| `--ci` | Headless mode | Off |
| `--json` | Emit `risks.json` payload to stdout | Off |

In `--ci` mode, also accept env vars `MCP_FROM_VERSION`, `MCP_TO_VERSION`, `MCP_MODE`.

When invoked via the slash command `/sdk-migration-manager <mode> [from] [to] [--ci] [--json]`,
parse positional args in that order. The command file is a thin wrapper that activates this skill.

## Authoritative reference

The 1.13.1 → 1.27.1 migration guide is the default playbook:

`notes/mcp-python-sdk-1_13_1-to-1_27_1_migration_guide.md`

**Re-read it on every invocation.** Do not bake heuristics into this SKILL.md — the guide
is authoritative and may evolve. For other v1.x ↔ v1.x version pairs, use the guide as
a structural template but extract per-version heuristics from the SDK release notes.

## Modes

Each mode produces a defined artifact set. Detailed runbooks live in `references/modes.md` —
**read that file before executing any mode**.

| Mode | Action | Artifacts (in run dir) |
|---|---|---|
| `audit` | Scan repo, classify findings. No plan. | `summary.md`, `risks.json` |
| `plan` | Build phased migration plan from current findings. | `plan.md`, `checklist.md`, `summary.md`, `risks.json` |
| `execute` | Walk `latest/plan.md` incrementally with human checkpoints. **Operates in place** on the `latest` dir; does not create a new run dir. | Updates `checklist.md`, appends `execute-log.md` |
| `verify` | Run conformance harness + spec-conformance checks. Pass/fail. | `summary.md`, `risks.json` |
| `rollback` | Generate pin-downgrade recipe + risk doc. **Does not edit code.** | `rollback.md`, `summary.md`, `risks.json` |

### Run-directory semantics

All artifacts live under `.claude/migration-reports/`. Modes that produce a fresh run
(`audit`, `plan`, `verify`, `rollback`) create a new `<UTC-timestamp>/` directory
(`YYYY-MM-DDTHH-MM-SSZ`) and update the pointer file `.claude/migration-reports/latest`
to contain that directory's name. Use a pointer file, **not a symlink** — Windows.

`execute` is the exception: it operates **in place** on the directory that `latest`
currently points to. It does not advance `latest`. If `latest/plan.md` is missing,
`execute` fails fast (exit 2 in `--ci`).

Implication: once `verify` runs after `execute`, `latest` advances away from the plan
directory. To resume `execute` against the original plan, pass the explicit path or
re-run `plan`. Mention this in user-facing help when relevant.

Use `scripts/new_run_dir.py` to create the run directory and update the pointer atomically.
Use `scripts/detect_version.py` for source-version detection. Use `scripts/probe_subagents.py`
to check which specialist subagents are present.

## Risk categories

Every finding must map to one of these categories. Detection patterns (ripgrep / ast-grep)
and remediation snippets are in `references/patterns.md` — **load that file when running
audit, plan, or verify**.

| Category | What to detect | Owning subagent |
|---|---|---|
| `oauth` | RFC 8707 resource binding; RFC 9728 PRM URL; `client_secret_basic`; `client_credentials` (JWT/Basic); CIMD; localhost DNS rebinding | `oauth-auditor` |
| `transport` | `streamable_http_client` factory→instance shape; `httpx.AsyncClient` integration; `onerror` coverage; idle timeout | `transport-auditor` |
| `conformance` | SEP-986 tool naming; SSE parse edges; JSON-RPC error-ID matching; MIME w/ RFC 2045 params; `Accept` header | `conformance-checker` |
| `fastmcp` | Resource/prompt context injection; `func_metadata`; schema generation; resource `meta` field; audio content | `fastmcp-reviewer` |
| `tasks` | Synchronous tool calls that could benefit from Task-based streaming; `TasksCallCapability` advertisement | inline (no subagent) |
| `lifecycle` | Session-ID-aware reconnect; 404-vs-400 for unknown sessions; `ClosedResourceError` propagation | inline (no subagent) |
| `dependency` | `mcp` pin missing `<2` cap; pin below `>=1.25`; new transitive deps (`pyjwt[crypto]`, `typing-extensions`, `typing-inspection`); `httpx<1.0.0` cap | inline (no subagent) |
| `tasks` adoption advisories | Long-running synchronous tools that emit no progress | inline |

### Severity grading

- `blocker` — code will break or fail validation after upgrade (e.g., custom transport assuming HTTP 400, hard-coded `mcp==1.13.1` with no `<2` cap that already breaks v2).
- `risk` — likely to surface latent issues (SEP-986 warning today, hardens later; `ClosedResourceError` propagation changes).
- `advisory` — opportunity, not a blocker (Tasks adoption, idle-timeout opt-in, CIMD support).

In `--ci`: `blocker` → exit 1; `risk` / `advisory` → exit 0 with a summary.

## Subagent orchestration

The four specialist subagents (`transport-auditor`, `oauth-auditor`, `conformance-checker`,
`fastmcp-reviewer`) are **enhancements, not prerequisites**. The skill is the orchestrator
and lightweight scanner; subagents are deep specialists.

### Dispatch

1. At start of every run, call `scripts/probe_subagents.py` to detect which agents exist
   (it lists `.claude/agents/*.md` and any global agents). Record results in `summary.md`
   under "Subagents used".
2. For each risk category with an owning subagent in the table above:
   - If present → invoke via Task tool with the contract below. Do **not** run inline
     checks for that category in this run.
   - If absent → run inline checks using the patterns in `references/patterns.md`.
3. The `tasks`, `lifecycle`, and `dependency` categories always run inline.

### Invocation contract for subagents

Pass these in the agent invocation message:

```
repo_path: <absolute path to target repo>
from_version: <e.g., 1.13.1>
to_version: <e.g., 1.27.1>
scope_glob: <e.g., src/**/*.py, default **/*.py>
migration_guide_path: <absolute path; default notes/mcp-python-sdk-1_13_1-to-1_27_1_migration_guide.md>
```

Each subagent returns a fenced JSON block conforming to the per-agent contract in
`notes/claude-code/agent-development-prompt.md`. The skill extracts that block and merges
its `findings` array into the top-level `risks.json`, prepending `"agent": "<name>"` per
finding for traceability. The narrative summary that follows the JSON is for humans only.

## risks.json schema

The canonical machine-readable output. Document this in every `audit`/`plan`/`verify`/`rollback`
run.

```json
{
  "from_version": "1.13.1",
  "to_version": "1.27.1",
  "scanned_at": "2026-05-27T14:30:00Z",
  "subagents_used": ["oauth-auditor", "transport-auditor"],
  "findings": [
    {
      "category": "oauth | transport | conformance | fastmcp | tasks | lifecycle | dependency",
      "severity": "blocker | risk | advisory",
      "file": "src/foo/bar.py",
      "line": 42,
      "rule": "SEP-986",
      "message": "Tool name 'My Tool' violates SEP-986 validation",
      "remediation": "Rename to 'my_tool' or 'my-tool'",
      "agent": "conformance-checker"
    }
  ]
}
```

Full schema and merge rules: `references/schemas.md`.

### Rule IDs — strict allow-list

Every finding's `rule` value MUST come from the table below. **Do not paraphrase, lowercase,
re-hyphenate, or invent IDs** — `mcp-pin-shape` is wrong; the correct ID is `Dependency-pin`.
If a finding genuinely doesn't map to any rule below, pick the closest one and explain the
nuance in `message`; never coin a new ID inline. (The table below is the authoritative
projection of `references/schemas.md` — keep both in sync if expanding.)

| Category | Allowed `rule` values |
|---|---|
| `conformance` | `SEP-986`, `SSE-parse`, `JSON-RPC-error-id`, `MIME-handling`, `Accept-header` |
| `transport` | `StreamableHTTP-factory`, `AsyncClient-shape`, `Session-lifecycle`, `onerror-coverage`, `Idle-timeout` |
| `oauth` | `RFC-8707`, `RFC-9728`, `OAuth-client-secret-basic`, `OAuth-client-credentials`, `CIMD`, `DNS-rebind` |
| `fastmcp` | `FastMCP-context-injection`, `FastMCP-func-metadata`, `FastMCP-schema-gen`, `FastMCP-resource-metadata` |
| `tasks` | `Tasks-adoption`, `TasksCallCapability` |
| `lifecycle` | `ClosedResourceError`, `Session-404`, `Reconnect` |
| `dependency` | `Dependency-pin`, `Dependency-transitive`, `Dependency-httpx-cap` |

Common drift to avoid:
- `mcp-pin-shape` / `mcp-pin-floor` → use **`Dependency-pin`**.
- `transitive-deps` → use **`Dependency-transitive`**.
- `lock-drift` → use **`Dependency-pin`** and explain the drift in `message`.
- `OAuth-broad` (catch-all) → emit one finding per specific OAuth rule (`RFC-8707`, etc.), or skip if no concrete violation.
- `Session-404-vs-400` → use **`Session-404`**.

## Workflow

Every invocation follows the same shape:

1. **Parse inputs.** Resolve `from_version` / `to_version` / `mode`. In interactive mode,
   ask only for what's missing. In `--ci`, exit 2 if anything required is unresolved.
2. **Re-read the migration guide.** Always. The guide is authoritative; the skill body is
   a thin orchestrator that defers to it.
3. **Probe subagents.** Record availability in `summary.md`.
4. **Create the run directory** (unless mode is `execute`). Use `scripts/new_run_dir.py`.
5. **Scan / act per mode.** Read `references/modes.md` for the per-mode runbook. Read
   `references/patterns.md` for detection heuristics.
6. **Emit artifacts** to the run dir. Pretty-print `risks.json` (2-space indent).
7. **Print a terse end-of-run summary** to stdout: from/to versions, run directory,
   counts by severity, subagents used, exit code in CI mode. With `--json`, also stream
   the full `risks.json` to stdout.

### Scanning tools

Standard tools: `ripgrep` (`rg`) and `ast-grep`. Both expected on engineering machines;
degrade gracefully if missing (warn + fall back to Python regex via `Grep` tool, or skip
the category with an advisory finding).

Project-linter fallback: if `mypy` / `ruff` / `pylint` are configured in the target repo,
shell out to them for additional signal. Do **not** require them.

Detailed pattern library: `references/patterns.md`. Worked-example dispatch for
1.13.1 → 1.27.1: `references/worked-example-1.13-to-1.27.md`.

## CI integration

The skill ships no GitHub Actions YAML. Recipe-only guidance lives in `references/ci-recipe.md`.
Summary:

```bash
# In CI
claude-code skill run sdk-migration-manager \
  --ci \
  --json \
  -- audit "$MCP_FROM_VERSION" "$MCP_TO_VERSION" \
  > risks.json
```

Then have the CI step assert `jq '.findings | map(select(.severity == "blocker")) | length' < risks.json -eq 0`,
or trust the skill's exit code (0 clean, 1 blockers, 2 config error).

## Recipe examples

Each mode supports both natural-language activation and explicit slash-command invocation.

**Audit (default mode):**
- User: "audit my repo for mcp 1.27 readiness"
- Slash: `/sdk-migration-manager audit`
- Slash with explicit versions: `/sdk-migration-manager audit 1.13 1.27`

**Plan:**
- User: "build a migration plan from mcp 1.13.1 to 1.27.1"
- Slash: `/sdk-migration-manager plan 1.13.1 1.27.1`

**Execute (against the most recent plan):**
- User: "walk me through the migration plan"
- Slash: `/sdk-migration-manager execute`

**Verify (post-upgrade):**
- User: "verify the mcp upgrade landed cleanly"
- Slash: `/sdk-migration-manager verify`

**Rollback recipe:**
- User: "give me a rollback path if the mcp upgrade goes sideways"
- Slash: `/sdk-migration-manager rollback`

**Headless CI audit:**
- Slash: `/sdk-migration-manager audit --ci --json`

## Working with medium-to-large codebases & monorepos

- Default `scope_glob` to `**/*.py`. For monorepos, ask once at the top of the run whether
  to scope to a specific package (e.g., `services/foo/**/*.py`) — store the answer in
  `summary.md` so subsequent modes use the same scope.
- Group findings by file in `summary.md` to keep human-readable reports useful at scale.
- For very large repos (>2k Python files), prefer `rg` over `ast-grep` for first-pass
  pattern hits, then run `ast-grep` only on the matching files.

## Tone & non-goals

**Tone.** Senior-staff-engineer level. Practical, operational, concise, production-oriented.
Avoid generic migration advice, superficial checklists, toy examples, vague recommendations.

**Non-goals.** This skill is **not**:

- an MCP server framework (use FastMCP)
- a credential vault (credentials are the host application's concern)
- a v1 → v2 migrator (out of scope until v2 stabilizes)
- a code-rewriting tool (it audits, plans, and validates; it does not refactor)

## Reference index

| File | When to read |
|---|---|
| `references/modes.md` | Before running any mode — per-mode runbook |
| `references/patterns.md` | When scanning the repo — ripgrep / ast-grep patterns by category |
| `references/schemas.md` | Building or merging `risks.json` |
| `references/worked-example-1.13-to-1.27.md` | Default playbook walkthrough |
| `references/ci-recipe.md` | When the user asks about CI integration |
