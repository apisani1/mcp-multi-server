# Output Schemas

Canonical JSON schemas for the artifacts this skill produces. Treat these as
load-bearing — downstream CI scripts depend on field names being stable.

## `risks.json`

Top-level shape:

```json
{
  "from_version": "1.13.1",
  "to_version": "1.27.1",
  "scanned_at": "2026-05-27T14:30:00Z",
  "subagents_used": ["oauth-auditor", "transport-auditor"],
  "findings": [
    {
      "category": "oauth",
      "severity": "blocker",
      "file": "src/auth/oauth_client.py",
      "line": 117,
      "rule": "RFC-8707",
      "message": "Token request missing `resource` parameter — RFC 8707 binding not enforced",
      "remediation": "Add `resource=server_uri` to the token request. See https://datatracker.ietf.org/doc/html/rfc8707",
      "agent": "oauth-auditor"
    }
  ]
}
```

### Field rules

- `from_version`, `to_version`: PEP 440 strings. The skill resolves shorthand like
  `1.13` to the latest patch on that minor (e.g., `1.13.1`).
- `scanned_at`: UTC ISO-8601 with `Z` suffix.
- `subagents_used`: list of agent names that ran in this scan. Empty list if none.
- `findings`: array; empty (`[]`) is valid and not an error.
- Each finding:
  - `category` ∈ {`oauth`, `transport`, `conformance`, `fastmcp`, `tasks`, `lifecycle`, `dependency`}.
  - `severity` ∈ {`blocker`, `risk`, `advisory`}.
  - `file`: repo-relative path (forward slashes, even on Windows).
  - `line`: 1-indexed. Use `0` for whole-file findings (e.g., dependency pins).
  - `rule`: ID from the rule-ownership table in `agent-development-prompt.md`. Inventing
    new rule IDs is forbidden; coordinate via the table.
  - `message`: human-readable, one sentence, present tense.
  - `remediation`: concrete fix. Include a code snippet or URL if useful. One paragraph max.
  - `agent`: optional. Present when the finding came from a specialist subagent.

### Allowed `rule` values (sync with `notes/claude-code/agent-development-prompt.md`)

| Rule | Category | Owner |
|---|---|---|
| `SEP-986` | conformance | `conformance-checker` |
| `SSE-parse` | conformance | `conformance-checker` |
| `JSON-RPC-error-id` | conformance | `conformance-checker` |
| `MIME-handling` | conformance | `conformance-checker` |
| `Accept-header` | conformance | `conformance-checker` |
| `StreamableHTTP-factory` | transport | `transport-auditor` |
| `AsyncClient-shape` | transport | `transport-auditor` |
| `Session-lifecycle` | transport | `transport-auditor` |
| `onerror-coverage` | transport | `transport-auditor` |
| `Idle-timeout` | transport | `transport-auditor` |
| `RFC-8707` | oauth | `oauth-auditor` |
| `RFC-9728` | oauth | `oauth-auditor` |
| `OAuth-client-secret-basic` | oauth | `oauth-auditor` |
| `OAuth-client-credentials` | oauth | `oauth-auditor` |
| `CIMD` | oauth | `oauth-auditor` |
| `DNS-rebind` | oauth | `oauth-auditor` |
| `FastMCP-context-injection` | fastmcp | `fastmcp-reviewer` |
| `FastMCP-func-metadata` | fastmcp | `fastmcp-reviewer` |
| `FastMCP-schema-gen` | fastmcp | `fastmcp-reviewer` |
| `FastMCP-resource-metadata` | fastmcp | `fastmcp-reviewer` |
| `Tasks-adoption` | tasks | inline |
| `TasksCallCapability` | tasks | inline |
| `ClosedResourceError` | lifecycle | inline |
| `Session-404` | lifecycle | inline |
| `Reconnect` | lifecycle | inline |
| `Dependency-pin` | dependency | inline |
| `Dependency-transitive` | dependency | inline |
| `Dependency-httpx-cap` | dependency | inline |

## `summary.md`

Markdown human-readable. Template lives in `references/modes.md`.

## `plan.md`

Markdown phased plan. Phasing principles in `references/modes.md`.

## `checklist.md`

GitHub-style task list (`- [ ]` / `- [x]`). Items match the phase numbering in `plan.md`
exactly. `execute` flips `- [ ]` → `- [x]` in place.

## `execute-log.md`

Append-only log. Each line: `<UTC-ISO8601>  phase=<N>  item=<N.M>  status=<done|skipped|deferred>  notes=<freeform>`.

## `rollback.md`

Markdown. Sections in this order:

1. **Pin to revert to** — single line, code block.
2. **Files to revert** — bulleted list of `path/to/file.py — one-line reason`.
3. **Known incompatibilities** — bulleted list. Each item names a specific 1.x+ pattern
   the current code uses that the downgrade target lacks.
4. **Risk assessment** — `low | medium | high` with a one-paragraph justification.
5. **Suggested git commands** — exact commands the user can copy. Do not run them.

## Merge rules (subagent findings → top-level `risks.json`)

1. Each subagent returns a JSON block with its own `findings` array. The skill extracts
   that array and concatenates into the top-level `findings`.
2. The skill prepends `"agent": "<name>"` to each finding so traceability is preserved
   even if the merged file is the only thing CI sees.
3. Findings are sorted before write: by `severity` (blocker → risk → advisory), then by
   `category`, then by `file`, then by `line`. Stable sort.
4. Two findings with the same `(file, line, rule)` are deduplicated; the skill keeps the
   one with the more severe `severity` (blocker > risk > advisory).
