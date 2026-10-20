## MCP Multi-Server v1.2.3

Infrastructure-only release: no changes to the library API or runtime behavior. It syncs the development and release tooling with generate-project v2.5.0 and hardens CI and release scripts.

### Changed
- **`make run` now takes `ARGS`**: use `make run ARGS="examples.client.chat_client"` instead of `make run examples.client.chat_client`. New shortcuts: `make run-chat`, `run-tool-server`, `run-resource-server`, `run-prompt-server`.
- `run.sh` recreates a `.venv` copied from another checkout instead of silently using the original one.

### Added
- Worktree lifecycle targets (`worktree-setup`, `worktree-archive`, `worktree-delete`).
- Claude PR Assistant workflow and Dependabot configuration.

### Security
- GitHub workflows pin actions to commit SHAs and no longer interpolate context values into shell scripts.
- Release rollback state is stored as JSON rather than pickle.
- The skills installer rejects manifest paths that could escape the destination directory.

### Documentation
- README gains PyPI, Python and ReadTheDocs badges.

**Full changelog**: https://github.com/apisani1/mcp-multi-server/compare/v1.2.2...v1.2.3
