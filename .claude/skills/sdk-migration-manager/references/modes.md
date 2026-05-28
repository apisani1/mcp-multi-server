# Per-Mode Runbooks

Read this file before executing any mode. Each section is a complete runbook for one
mode: inputs, outputs, step-by-step actions, exit codes.

## Contents

- [`audit`](#audit)
- [`plan`](#plan)
- [`execute`](#execute)
- [`verify`](#verify)
- [`rollback`](#rollback)
- [Shared: run-directory creation](#shared-run-directory-creation)
- [Shared: summary.md template](#shared-summarymd-template)

---

## `audit`

**Purpose.** Scan the target repo and classify findings by category and severity. No plan,
no edits. The lightest-weight mode — also the default.

**Inputs.** `from_version`, `to_version`, optional `scope_glob`.

**Outputs.** `summary.md`, `risks.json`.

**Steps:**

1. Run `scripts/detect_version.py` if `from_version` is missing. Error if undetectable
   in `--ci`.
2. Run `scripts/probe_subagents.py` and record which of the four specialists are present.
3. Re-read the migration guide.
4. Create a new run directory via `scripts/new_run_dir.py` (this updates `latest`).
5. For each risk category with an owning subagent that is present: invoke the subagent
   via the Task tool with the invocation contract from SKILL.md. Otherwise run the
   inline checks for that category using `references/patterns.md`.
6. Always run inline checks for `tasks`, `lifecycle`, `dependency`.
7. Merge all findings into `risks.json` and write to the run dir.
8. Write `summary.md` from the template below.
9. Print terse end-of-run summary to stdout. If `--json`, stream `risks.json` to stdout.

**Exit codes (`--ci`):** 0 if no `blocker`; 1 if any `blocker`; 2 if config error
(e.g., undetectable `from_version`).

---

## `plan`

**Purpose.** Build a phased, prioritized migration plan from the findings.

**Inputs.** Same as audit; also reads the most recent `risks.json` if one exists in
`latest/`. If not, runs the audit steps first to produce one in the new run dir.

**Outputs.** `summary.md`, `risks.json`, `plan.md`, `checklist.md`.

**Phasing principles** (apply in order):

1. **Phase 0 — Dependency pin.** First commit: bump `mcp` to the target version pin
   (`>=<to_version>,<2`). Verifies that the env resolves.
2. **Phase 1 — Blockers.** Fix anything categorized `blocker`. No optional work here.
3. **Phase 2 — OAuth & transport correctness.** RFC 8707 wiring, `streamable_http_client`
   shape, `onerror` coverage, session lifecycle. Security and reliability come before
   ergonomics.
4. **Phase 3 — Spec conformance.** SEP-986 renames, MIME validation tightening, JSON-RPC
   error ID handling. Mostly cleanup — warnings today, hard errors later.
5. **Phase 4 — FastMCP & advisory adoption.** Resource metadata, audio content type,
   context injection. Anything `advisory` that's worth doing.
6. **Phase 5 — Tasks adoption (opt-in).** Only for tools where streaming output is a
   real product win. Don't push Tasks adoption as a default; it's net-new code.

Each phase contains:
- the findings that drive it (by `rule` and file:line)
- the acceptance criteria
- a rollback note (what to revert if the phase breaks something)

**`checklist.md` format.** GitHub-style task list, one `- [ ]` per actionable item.
Group by phase. Match `plan.md` numbering exactly so `execute` can cross-reference.

```markdown
## Phase 1 — Blockers

- [ ] 1.1 Rename tool `My Tool` in `src/server/tools.py:42` (SEP-986)
- [ ] 1.2 Update custom `streamable_http_client` call site in `src/transport.py:88`

## Phase 2 — OAuth & transport correctness
...
```

---

## `execute`

**Purpose.** Walk the plan with human checkpoints between phases. **The only mode that
writes in place** — it operates on the directory that `latest` currently points to and
does not advance `latest`.

**Preconditions.**
- `latest/plan.md` must exist. If not, fail fast with exit 2 in `--ci`, or tell the user
  to run `plan` first in interactive mode.

**Outputs.** Updates `checklist.md` in place (toggles `- [ ]` → `- [x]`). Appends to
`execute-log.md` in the same directory.

**Steps:**

1. Read `latest/plan.md` and `latest/checklist.md`.
2. For each phase in order:
   - Print the phase's items to the user.
   - For each item:
     - Ask the user to acknowledge they've made the change (or skip/defer with a
       reason). The skill does **not** edit code — execution is human-driven.
     - On acknowledgement, tick the item in `checklist.md` and append a line to
       `execute-log.md`:
       `2026-05-27T15:42:11Z  phase=1  item=1.1  status=done  notes=...`
     - On skip/defer, log the reason but do not tick.
   - At end of phase, print phase-level summary and ask for go/no-go on the next phase.
3. After the final phase, print overall summary and remind the user to run `verify`.

**`--ci` behavior.** Skip user prompts. Read `checklist.md`, log "ci-noop" entries for any
items not already ticked, exit 0. Useful for CI to confirm a plan exists and has been
worked through, but not for actually executing items.

---

## `verify`

**Purpose.** Post-upgrade validation. Confirms the upgrade landed cleanly.

**Outputs.** `summary.md`, `risks.json`.

**Checks:**

1. **Dependency pin.** Confirm `mcp>=<to_version>,<2` is present in `pyproject.toml` and
   matches the installed version in the lockfile.
2. **Re-audit.** Re-run the audit checks (subagents + inline). Any remaining `blocker`
   findings → verify fails.
3. **Conformance harness.** If the MCP `everything-server` conformance harness is
   available in the repo (look for `tests/conformance/` or any `everything_server` import
   path), run it via the project's existing test runner. If absent, record a
   non-fatal advisory in `summary.md` ("conformance harness not present — skipped").
4. **Smoke test.** Run the project's own tests if `make test`, `pytest`, or `uv run pytest`
   is detectable. Report pass/fail without re-deriving test logic.

**Exit codes (`--ci`):** 0 clean; 1 if any `blocker` remains or conformance/smoke fails;
2 config error.

---

## `rollback`

**Purpose.** Produce a downgrade recipe and risk doc. **Does not edit code.** Teams
execute the rollback through their normal git workflow.

**Outputs.** `summary.md`, `risks.json`, `rollback.md`.

**`rollback.md` contents:**

1. The exact `mcp` version pin to revert to (the original `from_version`).
2. A list of post-upgrade code changes that must be reverted together for a clean
   downgrade, with file paths and a one-line description per change. Source these from
   `git diff <pre-upgrade-sha>..HEAD -- $(rg -l 'mcp' --files-with-matches src/)`.
3. Known incompatibilities between the current code and the downgrade target — e.g.,
   "uses `streamable_http_client(httpx.AsyncClient(...))` shape from 1.24+; 1.13 only
   accepts the factory form."
4. Risk assessment with a clear verdict:
   - **low** — `git revert <upgrade-commit>` is likely sufficient.
   - **medium** — partial revert needed; identify which files.
   - **high** — significant divergence; rollback requires substantial manual work and a
     freeze on intervening commits.

**Steps:**

1. Resolve the pre-upgrade commit SHA. Look for the commit that bumped the `mcp` pin in
   `pyproject.toml`. Ask the user if ambiguous.
2. Compute the diff of MCP-touching files between that SHA and HEAD.
3. Cross-reference each diff hunk against the migration guide's "Likely to break code"
   section — anything that maps there increases the risk score.
4. Write `rollback.md` per the template above.

---

## Shared: run-directory creation

Always go through `scripts/new_run_dir.py`. Pseudocode:

```
ts = now_utc().strftime("YYYY-MM-DDTHH-MM-SSZ")
mkdir .claude/migration-reports/<ts>
write_text .claude/migration-reports/latest <- <ts>\n
print <ts>
```

The script handles atomicity (tempfile + rename for the pointer). `execute` mode must
**not** call this — it reads `latest` and operates in place.

---

## Shared: summary.md template

```markdown
# MCP SDK Migration — <mode>

- **From:** <from_version>
- **To:** <to_version>
- **Mode:** <mode>
- **Run directory:** `.claude/migration-reports/<timestamp>/`
- **Scanned at:** <UTC timestamp>
- **Scope:** <scope_glob, default **/*.py>
- **Subagents used:** <list, or "none — inline checks only">

## Findings by severity

| Severity | Count |
|---|---|
| blocker | <n> |
| risk | <n> |
| advisory | <n> |

## Top findings

<Top 5–10 by severity. Each: rule, file:line, one-line message.>

## Recommended next step

<For audit: "Run `/sdk-migration-manager plan <from> <to>` to build a migration plan.">
<For plan: "Open `plan.md` and `checklist.md`. Then run `/sdk-migration-manager execute`.">
<For execute: "Run `/sdk-migration-manager verify` once all phases are complete.">
<For verify: "Clean — upgrade complete." OR "Re-open <category> findings in <files>.">
<For rollback: "Review `rollback.md`; execute via normal git workflow.">
```
