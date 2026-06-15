# mcp-multi-server v1.2.0

This release makes fleet startup more robust. You can now choose how the client reacts
when a server fails to connect, and registration is atomic so a failure mid-discovery
never leaves a half-registered server behind. It also upgrades the MCP SDK to 1.27.1.

## Added

- **`strict_connect` connection-failure policy** on `MultiServerClient` and
  `SyncMultiServerClient` (constructor, `from_config`, `from_dict`):
  - `False` (default): a server that fails to connect — or whose transport dies during
    capability discovery — is dropped, and the remaining servers still connect.
  - `True`: such a failure is raised instead of skipped.
- **`MCP_MULTI_SERVER_STRICT_CONNECT` environment variable** to set the default policy
  when `strict_connect` is left as `None` (truthy values: `1`/`true`/`yes`/`on`).

```python
# Fail fast if any server can't be reached:
client = MultiServerClient.from_config("mcp_servers.json", strict_connect=True)

# Or set the default for the whole process:
#   export MCP_MULTI_SERVER_STRICT_CONNECT=1
```

## Changed

- **Atomic server registration.** Capabilities are discovered into local state and
  committed to the client only after discovery completes cleanly, so a failure partway
  through never leaves partial ("zombie") server state behind.
- **Clearer failure handling during discovery.** A server that legitimately lacks a
  capability (`McpError`, e.g. method-not-found) is warned and skipped, and the server is
  still registered with whatever it does provide. A transport-level or otherwise
  unexpected failure is re-raised so the `strict_connect` policy can apply.
- **MCP SDK upgraded to 1.27.1** (minimum is now `>=1.27.1`).

## Fixed

- examples: the media handler now strips RFC 2045 parameters from MIME types
  (e.g. `text/html; charset=utf-8` → `text/html`) so parameterized media types are
  handled correctly.

## Upgrading

No breaking API changes — existing code keeps the previous behavior (lenient connect).
Because the default `strict_connect` is `False`, servers that fail to connect are still
skipped as before; opt into `strict_connect=True` (or the environment variable) if you
want startup to fail fast. Ensure your environment provides `mcp >= 1.27.1`.
