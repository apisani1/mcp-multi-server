# Worked Example — 1.13.1 → 1.27.1

This is the default playbook the skill follows when a user runs

```
/sdk-migration-manager plan 1.13.1 1.27.1
```

It walks the dispatch logic across every risk category against the heuristics in
[`notes/mcp-python-sdk-1_13_1-to-1_27_1_migration_guide.md`](../../../../notes/mcp-python-sdk-1_13_1-to-1_27_1_migration_guide.md).
Use this as a reference shape; do not reproduce findings verbatim — extract them fresh
from the user's actual repo each run.

## Phase 0 — Dependency pin

**One commit.** Update `pyproject.toml`:

```diff
- mcp = "^1.13.1"
+ mcp = ">=1.27,<2"
```

Plus equivalent for the lock format the project uses. Regenerate the lock. Verify env
resolves (`uv sync` or `poetry lock --no-update && poetry install`).

Confirm new transitive deps appear in the lock:
- `pyjwt[crypto]>=2.10.1`
- `typing-extensions>=4.9.0`
- `typing-inspection>=0.4.1`

If the project pins `httpx`, ensure the range overlaps `>=0.27.1,<1.0.0`.

## Phase 1 — Blockers

Findings the audit must surface as blockers if present:

| Rule | Why it blocks | Remediation |
|---|---|---|
| `RFC-8707` (missing `resource=`) | Token requests without `resource=` fail on 1.27 if the server enforces RFC 8707 | Add `resource=server_uri` to every token request |
| `Session-404` (client branches on 400) | Client logic that returns "session unknown" only on HTTP 400 silently breaks on 1.26+ | Branch on 404 (or treat both 400 and 404 the same for backward compat) |
| `StreamableHTTP-factory` (incompatible kwargs) | Code that passes `httpx_client_factory` *and* an `AsyncClient` instance fails on 1.24+ | Pass an `AsyncClient` instance directly |

Optional: if there's a custom JSON-RPC dispatch that doesn't echo the request `id` on
errors (`JSON-RPC-error-id`), promote to blocker — that code path now fails strictly.

## Phase 2 — OAuth & transport correctness

Order within the phase: OAuth first (security), then transport (reliability).

### OAuth

1. **`RFC-9728` PRM URL.** Confirm the client resolves protected-resource metadata via
   the SDK (`mcp.client.auth.discover_oauth_metadata`) rather than constructing the URL
   manually. If manual, replace with the SDK helper.
2. **`OAuth-client-secret-basic` / `OAuth-client-credentials`.** If the repo has its
   own OAuth client provider, confirm both auth methods are supported. The SDK's
   `OAuthClientProvider` now handles them natively.
3. **`CIMD`.** Advisory only — opportunity to support URL-based client IDs.
4. **`DNS-rebind`.** Confirm the repo doesn't explicitly disable localhost DNS rebinding
   protection. The auto-enable on 1.23+ is the safe default.

### Transport

1. **`AsyncClient-shape`.** Move from `httpx_client_factory=lambda: httpx.AsyncClient(...)`
   to passing the `AsyncClient` instance directly. Lets the project share connection
   pools and inject auth headers cleanly.
2. **`onerror-coverage`.** Wire the `onerror` callback on every `streamable_http_client`
   call site. Surface transport errors into the project's logger.
3. **`Idle-timeout` / `Session-lifecycle`.** Opt in to idle timeout if connections idle
   long enough to hit intermediary timeouts. Default off — only wire if measured.

## Phase 3 — Spec conformance

1. **`SEP-986` tool names.** Rename any tool whose name violates `^[A-Za-z0-9._-]{1,128}$`.
   The SDK only warns today; future spec revisions may hard-fail. Coordinate renames
   with consumers — tool name is part of the public API.
2. **`MIME-handling`.** Loosen any strict-equality MIME checks to accept RFC 2045
   parameters (`text/plain; charset=utf-8`).
3. **`JSON-RPC-error-id`.** Audit custom JSON-RPC dispatch layers. Confirm error
   responses echo the request `id`.
4. **`Accept-header`.** If the client previously sent both `application/json` and
   `text/event-stream`, it can relax to JSON-only for JSON-only endpoints.

## Phase 4 — FastMCP & advisory adoption

Only relevant if the repo uses FastMCP for any server code.

1. **`FastMCP-context-injection`.** Confirm resources/prompts that accept `ctx: Context`
   still work — the 1.14 fix may have changed behavior for previously-broken configs.
2. **`FastMCP-func-metadata`.** Spot-check tools/resources with complex `Annotated[]`
   parameters. The 1.21 refactor may produce slightly different schemas. Compare against
   golden schemas if you have them.
3. **`FastMCP-resource-metadata`.** Adopt the new `meta` field on resources for
   traceability (`serverName`, `serverVersion`, etc.). Advisory only.

## Phase 5 — Tasks adoption (opt-in)

**Not on by default.** Only do this work if the team has tools that emit progress
incrementally and would benefit from Task-style streaming. Adoption requires both server-
and client-side opt-in. For pure clients (like mcp-multi-server), the work is:

- Recognize the nested `call: {}` capability advertised by Tasks-emitting servers.
- Follow the task lifecycle (`tasks/get` polling or streaming notifications).
- Plumb incremental payloads through to the caller without buffering.

## Verify (after the phases land)

```
/sdk-migration-manager verify
```

Should produce:
- 0 blockers
- A small number of advisories (Tasks adoption, CIMD, idle-timeout) is fine and expected.
- `mcp` pinned to `>=1.27,<2` in `pyproject.toml` and lockfile.
- Conformance harness (if present) passes.

## Rollback risk profile

For this version pair, expected verdict:

- **low** risk if Phase 0 + Phase 1 are the only commits — `git revert` is clean.
- **medium** risk if Phase 2 OAuth changes landed — those refactor call sites that the
  downgrade target's API doesn't accept the same way (e.g., `resource=` kwarg).
- **high** risk if Phase 5 Tasks code shipped — Tasks doesn't exist on 1.13, so any code
  that depends on the task lifecycle must be ripped out, not just reverted.
