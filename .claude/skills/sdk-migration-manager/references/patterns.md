# Detection Patterns — by Risk Category

Concrete `ripgrep` and `ast-grep` patterns the skill runs when inline (i.e., when the
owning subagent is absent). Subagents own the same rules but go deeper. Keep this file
in sync with the rule-ownership table in SKILL.md.

All `rg` examples assume the repo root as CWD and use `--type py` to scope to Python.
`ast-grep` examples use Python target language.

## Contents

- [conformance](#conformance) — SEP-986, SSE parse, JSON-RPC error ID, MIME, Accept header
- [transport](#transport) — StreamableHTTP factory, AsyncClient shape, session lifecycle, onerror, idle timeout
- [oauth](#oauth) — RFC 8707, RFC 9728, client_secret_basic, client_credentials, CIMD, DNS rebind
- [fastmcp](#fastmcp) — context injection, func_metadata, schema gen, resource metadata
- [tasks](#tasks) — adoption advisories, TasksCallCapability
- [lifecycle](#lifecycle) — 404-vs-400, ClosedResourceError, reconnect
- [dependency](#dependency) — mcp pin, transitive deps

---

## conformance

### `SEP-986` — Tool name validation

Tools whose names violate `^[A-Za-z0-9._-]{1,128}$` emit warnings on 1.23+ and may hard-fail
in a future revision.

```
rg --type py -n -e '@\s*(mcp|server|app|fastmcp)\.tool\s*\(\s*name\s*=\s*["'"'"'][^A-Za-z0-9._-]'
rg --type py -n -e '@\s*(mcp|server|app|fastmcp)\.tool\s*\(\s*name\s*=\s*["'"'"'].{129,}'
rg --type py -n -e 'name\s*=\s*["'"'"'][^"]*\s[^"]*["'"'"']\s*\)' -g '**/tools.py'
```

Also flag advisory cases: leading/trailing `-` or `.`, and names containing spaces, commas,
or other non-ASCII.

Severity: `risk` (warnings today, hardens later).

### `SSE-parse` — Empty SSE data parsing

If the repo implements its own SSE consumer (rare, but check), confirm it handles
empty-data events without crashing.

```
rg --type py -n -e 'event:\s*$' -e '"data": ""' -e 'sse_parse' -e 'parse_sse'
```

Severity: `advisory` unless the repo is hand-rolling SSE parsing.

### `JSON-RPC-error-id` — JSON-RPC error response ID matching

Custom JSON-RPC dispatch layers that don't echo the request `id` on error responses will
break on 1.24+.

```
rg --type py -n -e 'jsonrpc' -e 'JsonRpc' -e 'JSONRPCError'
ast-grep --lang python -p 'JSONRPCError(code=$_, message=$_)'    # missing id= arg
```

Severity: `risk`.

### `MIME-handling` — RFC 2045 MIME parameters

Code that validates MIME types with strict equality (`mime == "text/plain"`) will reject
`text/plain; charset=utf-8`, which the SDK now accepts.

```
rg --type py -n -e 'mime\s*==' -e 'content_type\s*==' -e 'mimetype\s*==' -e '"text/plain"\s*==' 
```

Severity: `advisory` (now-accepted forms may surface in interop tests).

### `Accept-header` — JSON-only responses

If the client previously asserted both `application/json` and `text/event-stream` in
`Accept`, it can be relaxed to JSON-only for JSON-only endpoints (1.20+).

```
rg --type py -n -e 'Accept.*event-stream' -e '"Accept":' -e "'Accept':"
```

Severity: `advisory`.

---

## transport

### `StreamableHTTP-factory` — Factory vs instance shape

`streamable_http_client` accepts an `httpx.AsyncClient` instance directly on 1.24+. The
old factory shape still works but is deprecated as the recommended path.

```
rg --type py -n -e 'streamable_http_client\s*\(' -e 'httpx_client_factory'
ast-grep --lang python -p 'streamable_http_client(httpx_client_factory=$_)'
ast-grep --lang python -p 'streamable_http_client($URL, $$$)'   # inspect kwargs
```

Severity: `risk` (factory works, but inconsistent integration with shared httpx pools).

### `AsyncClient-shape` — Sharing httpx.AsyncClient

If the repo manages its own `httpx.AsyncClient` (auth headers, connection pool, retries),
prefer passing the instance directly into `streamable_http_client`.

```
rg --type py -n -e 'httpx\.AsyncClient' -e 'AsyncClient\('
ast-grep --lang python -p 'httpx.AsyncClient($$$)'
```

Severity: `advisory`.

### `Session-lifecycle` — Idle timeout + reconnect

StreamableHTTP idle timeout is opt-in (1.27+). If the repo has connections that idle long
enough to be dropped by intermediaries (load balancers, proxies), wire the timeout.

```
rg --type py -n -e 'idle_timeout' -e 'Mcp-Session-Id' -e 'session_id'
```

Severity: `advisory`.

### `onerror-coverage` — Transport error callback

`onerror` callbacks surface transport-layer errors that previously could be silent. Repos
that wire callbacks for tool calls but not transports leave a blind spot.

```
rg --type py -n -e 'onerror' -e 'on_error\s*=' -e 'transport.*error'
```

Severity: `risk` (silent transport errors are an operational hazard).

### `Idle-timeout` — Wire the new opt-in

Same as `Session-lifecycle` but focused on the 1.27 idle-timeout parameter specifically.
Surface as `advisory`.

---

## oauth

### `RFC-8707` — Resource binding

The headline 1.27 change. Tokens must be bound to the resource URI they were issued for.

```
rg --type py -n -e 'resource\s*=' -e 'audience' -e 'token_endpoint' -e 'resource_indicators'
ast-grep --lang python -p 'OAuthClientProvider($$$)'
```

If OAuth code exists and `resource=` is not set on token requests → `risk`. If it's set
but to the wrong URI shape → `blocker`.

### `RFC-9728` — Protected Resource Metadata URL

PRM URL construction was tightened in 1.17. Manual URL construction may diverge from spec.

```
rg --type py -n -e '/.well-known/oauth-protected-resource' -e 'protected_resource_metadata'
```

Severity: `risk` if manual; `advisory` if delegated to the SDK.

### `OAuth-client-secret-basic` — Auth method support

Added in 1.23. Check that any custom client implementation supports it.

```
rg --type py -n -e 'client_secret_basic' -e 'client_secret_post'
```

Severity: `advisory`.

### `OAuth-client-credentials` — Service-to-service flow

Added in 1.23 with JWT/Basic variants. If the repo has machine-to-machine auth, prefer
this over hand-rolled flows.

```
rg --type py -n -e 'client_credentials' -e 'grant_type.*client_credentials'
```

Severity: `advisory`.

### `CIMD` — Client ID Metadata Document

URL-based client IDs (SEP-991, 1.23). Surface as `advisory` if not used.

```
rg --type py -n -e 'client_id_metadata_document' -e '"client_id_metadata_document_supported"'
```

### `DNS-rebind` — Localhost rebinding protection

Auto-enabled in 1.23 for localhost servers. Worth confirming the repo doesn't explicitly
disable it.

```
rg --type py -n -e 'dns_rebinding' -e 'allow_origin' -e 'allow_origin_list'
```

Severity: `risk` if explicitly disabled.

---

## fastmcp

### `FastMCP-context-injection`

Context injection for resources and prompts was broken in some configurations pre-1.14.
If the repo declares resources/prompts with a `Context` parameter, confirm injection
works.

```
rg --type py -n -e '@mcp\.(resource|prompt)' -e 'def\s+.*\(\s*ctx:\s*Context'
ast-grep --lang python -p '@mcp.resource($$$)
def $FN($$$ ctx: Context $$$):
  $$$'
```

Severity: `advisory`.

### `FastMCP-func-metadata`

The `func_metadata()` schema derivation was refactored in 1.21. Custom Pydantic field
annotations that worked in 1.13 may produce slightly different schemas. Flag complex
annotation usage so the team can verify.

```
rg --type py -n -e 'Annotated\[' -e 'Field\(' -g '**/tools.py' -g '**/resources.py' -g '**/prompts.py'
```

Severity: `advisory`.

### `FastMCP-schema-gen`

Lazy `jsonschema` import (1.22) means schema generation may surface errors lazily.
Mostly an advisory.

### `FastMCP-resource-metadata`

Resource and ResourceTemplate now carry an optional `meta: dict[str, Any] | None` field
(1.26). Surface as `advisory`: opportunity for traceability metadata.

```
rg --type py -n -e '@mcp\.resource' -e 'FunctionResource\.from_function' -e 'ReadResourceContents'
```

---

## tasks

### Adoption advisories

Synchronous tools that emit progress notifications today, or that take >5 seconds in
typical use, are candidates for Tasks adoption. Heuristics:

```
rg --type py -n -e 'progress_notification' -e 'ctx\.report_progress' -e 'asyncio\.sleep\([5-9]'
```

Severity: `advisory`.

### `TasksCallCapability`

If the client consumes Tasks-emitting servers, confirm it checks the nested `call: {}`
capability before invoking task-style tools.

```
rg --type py -n -e 'TasksCallCapability' -e 'tasks_call' -e 'capabilities\.tasks'
```

Severity: `risk` if Tasks is used but capability check is absent.

---

## lifecycle

### `ClosedResourceError` propagation

Code that catches `ClosedResourceError` may see fewer or different occurrences on 1.23.2 /
1.27. Flag any explicit handlers for review.

```
rg --type py -n -e 'ClosedResourceError' -e 'except\s+.*Closed'
```

Severity: `advisory`.

### Session 404 vs 400

Any client logic that branches on the HTTP status code for "unknown session" now sees 404
instead of 400.

```
rg --type py -n -e 'status_code\s*==\s*400' -e 'response\.status\s*==\s*400'
```

Surface as `risk` if it appears alongside MCP transport code.

### Reconnect / session resumption

If the repo manages long-lived sessions, confirm it handles `Mcp-Session-Id`-aware
reconnect.

```
rg --type py -n -e 'reconnect' -e 'Mcp-Session-Id'
```

Severity: `advisory`.

---

## dependency

### `mcp` pin shape

- Missing upper cap (`<2`): **risk** — v2 will break.
- Pinned below `>=1.25`: **advisory** in `audit`, **blocker** in `verify` post-upgrade if
  the target is `>=1.25,<2`.
- Pinned to a fixed version (`mcp==1.X.Y`): **advisory** — denies security patches.

Check:

```
rg -n -e '"mcp"' -e "'mcp'" -e 'mcp\s*=' pyproject.toml requirements*.txt uv.lock poetry.lock
```

### New transitive deps

Confirm the project's lock includes `pyjwt[crypto]>=2.10.1`, `typing-extensions>=4.9.0`,
`typing-inspection>=0.4.1` after upgrade (OAuth JWT flow + new transitive deps).

```
rg -n -e 'pyjwt' -e 'typing-extensions' -e 'typing-inspection' pyproject.toml uv.lock poetry.lock
```

### `httpx` upper cap

1.27.1 added `httpx<1.0.0`. Repos with a wider httpx range should match.

```
rg -n -e 'httpx' pyproject.toml
```

Severity: `advisory`.
