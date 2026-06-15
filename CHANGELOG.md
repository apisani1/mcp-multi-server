# Changelog

## [1.2.0] - 2026-06-15

### Added
- `strict_connect` connection-failure policy on `MultiServerClient` and
  `SyncMultiServerClient` (constructor, `from_config`, `from_dict`). When `False`
  (default), a server that fails to connect or whose transport dies during capability
  discovery is dropped and the remaining servers still connect; when `True`, the
  failure is raised.
- `MCP_MULTI_SERVER_STRICT_CONNECT` environment variable, used as the default policy
  when `strict_connect` is left as `None` (truthy values: `1`/`true`/`yes`/`on`).

### Changed
- Server registration is now deferred and atomic. Capabilities are discovered into
  local state and committed to the client only after discovery completes cleanly, so a
  mid-discovery failure never leaves partial ("zombie") server state behind.
- Capability discovery now distinguishes a server that legitimately lacks a capability
  (`McpError`, e.g. method-not-found — warned and skipped, server still registered with
  whatever it provides) from a transport-level or otherwise unexpected failure, which is
  re-raised so `connect_all()` can apply the `strict_connect` policy.
- Upgraded the `mcp` dependency from `1.13.1` to `1.27.1`; the minimum supported version
  is now `>=1.27.1`.

### Fixed
- examples: the media handler now strips RFC 2045 parameters from MIME types
  (e.g. `text/html; charset=utf-8` → `text/html`) so equality and membership checks no
  longer reject parameterized media types.

### Documentation
- examples: the resource server now demonstrates resource `meta` metadata.
- Linked project notes from `CLAUDE.md`.

### Internal
- Added `.claude` tooling: the `sdk-migration-manager` skill and MCP migration subagents.
- Synced dev-environment infrastructure with generate-project v2.1.0 (`run.sh`,
  `Makefile`, `scripts/release.py`, CI workflows, `install_claude_skills.py`) and reduced
  vulnerabilities in `docs/requirements.txt`.

## [1.1.0.post1] - 2026-03-11

 ### Changes
This is a maintenance release with no changes to the public API. All updates are internal to the development infrastructure and tooling.

**CI/CD Improvements**   
The GitHub Actions workflows for tests, release, and docs have been overhauled and synced with the latest project template. Integration tests are now correctly excluded from the standard CI test run, and a dedicated tests:ci command was added to run.sh to make this distinction explicit. A missing system dependency step required for Pillow compilation was restored to the test workflow.

**Release Script Overhaul**   
The release script (scripts/release.py) was significantly refactored. It now uses a RollbackState mechanism to safely undo partial changes if the release process fails mid-way, and adds an interactive confirmation mode so each step can be reviewed before execution.

**Developer Tooling**   
The Makefile and run.sh script were synced with the latest generate-project template, bringing in additional development commands and improving consistency. A fix was also applied for Python 3 PATH resolution under Poetry 2.x. The notes/ directory is now excluded from version control via .gitignore.


## [1.1.0] - 2026-01-22

 ### Changes
- 📝 docs: add SyncMultiServerClient documentation
- ✅ test: add comprehensive tests for SyncMultiServerClient
- 🧵 feat: add SyncMultiServerClient for synchronous code


## [1.0.0] - 2025-12-08

 ### Changes
- First Release
